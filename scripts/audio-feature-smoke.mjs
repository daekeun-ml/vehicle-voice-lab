import {readFile,writeFile} from 'node:fs/promises';
const audioModelId=process.argv[2]||'mimo-audio',base='http://localhost:8787/api/';
const s=await(await fetch(base+'session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json(),headers={'Content-Type':'application/json','X-Session-Id':s.id},rows=[];
const cases=[['driver-24',state=>state.temperature.driver===24&&state.temperature.passenger===22],['defrost-on',state=>state.defrost],['defrost-off',state=>!state.defrost],['temperature-up',state=>state.temperature.driver===25&&state.temperature.passenger===23]];
for(const [name,check] of cases){
 const audio=(await readFile(`output/minicpm-audit/${name}.wav`)).toString('base64');
 const r=await fetch(base+'audio-control',{method:'POST',headers,body:JSON.stringify({audioModelId,audio,speak:false,inputMode:'file'}),signal:AbortSignal.timeout(180000)});
 const e=(await r.text()).split('\n\n').filter(Boolean).map(b=>({event:b.match(/^event: (.*)/m)?.[1],data:JSON.parse(b.match(/^data: (.*)/m)?.[1]||'{}')}));const reply=e.find(b=>b.event==='reply')?.data;
 const row={name,understood:e.find(b=>b.event==='understood')?.data.text,actions:reply?.actions,state:reply?.state,llmMs:reply?.llmMs,passed:!!reply?.actions.length&&check(reply.state),error:e.find(b=>b.event==='error')?.data.error};rows.push(row);console.log(JSON.stringify(row));
}
await writeFile(`research/${audioModelId}-vehicle-features.json`,JSON.stringify({at:new Date().toISOString(),method:'Synthetic Korean WAV, sequential vehicle state, no TTS',audioModelId,passed:rows.filter(r=>r.passed).length,total:rows.length,rows},null,2));
