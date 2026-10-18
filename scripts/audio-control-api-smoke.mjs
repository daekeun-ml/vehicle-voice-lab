import {readFile,writeFile} from 'node:fs/promises';
const catalog=JSON.parse(await readFile('model-catalog.json','utf8')),audio=(await readFile('public/sample-command.wav')).toString('base64'),rows=[];
async function session(){return (await fetch('http://localhost:8787/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();}
function headers(id){return {'Content-Type':'application/json','X-Session-Id':id};}
function events(raw){return raw.split('\n\n').filter(Boolean).map(b=>({event:b.match(/^event: (.*)/m)?.[1],data:JSON.parse(b.match(/^data: (.*)/m)?.[1]||'{}')}));}
for(const audioModelId of process.argv.slice(2).length?process.argv.slice(2):['step-audio2-mini','mimo-audio','qwen3-omni']){
 const s=await session();const r=await fetch('http://localhost:8787/api/audio-control',{method:'POST',headers:headers(s.id),body:JSON.stringify({audioModelId,audio,inputMode:'file',ttsProvider:'polly'}),signal:AbortSignal.timeout(360000)});
 const e=events(await r.text()),metrics=e.find(x=>x.event==='done')?.data.metrics,result=e.find(x=>x.event==='reply')?.data;
 const row={audioModelId,status:r.status,error:e.find(x=>x.event==='error')?.data.error,model:metrics?.planner,revision:metrics?.plannerRevision,asrMs:metrics?.asrMs,quantization:metrics?.quantization,understood:e.find(x=>x.event==='understood')?.data.text,actions:result?.actions,state:result?.state,llmMs:metrics?.llmMs,loadMs:metrics?.modelLoadMs,ttsMs:metrics?.ttsMs,audioReceived:e.some(x=>x.event==='audio'&&x.data.audio?.length>1000),commandCorrect:result?.state.temperature.passenger===25&&result?.state.temperature.driver===22};row.integrationPassed=row.model===catalog.models.find(m=>m.id===audioModelId)?.repo&&row.asrMs===null&&row.audioReceived&&!row.error;rows.push(row);console.log(JSON.stringify(row));
}
const s=await session();const pending=fetch('http://localhost:8787/api/audio-control',{method:'POST',headers:headers(s.id),body:JSON.stringify({audioModelId:rows.at(-1).audioModelId,audio,inputMode:'file',speak:false}),signal:AbortSignal.timeout(120000)}).then(r=>r.text());
await new Promise(resolve=>setTimeout(resolve,100));await fetch('http://localhost:8787/api/cancel',{method:'POST',headers:headers(s.id),body:'{}'});await pending;
const exported=await(await fetch('http://localhost:8787/api/export',{headers:headers(s.id)})).json();const cancellation={stateUnchanged:exported.state.revision===0&&exported.state.temperature.passenger===22,turns:exported.turns.length};console.log(JSON.stringify({cancellation}));
await writeFile('research/audio-control-api-integration.json',JSON.stringify({at:new Date().toISOString(),input:'Synthetic Korean WAV via actual local API; model controls and Polly output',rows,cancellation},null,2));
if(rows.some(r=>!r.integrationPassed)||!cancellation.stateUnchanged)process.exitCode=1;
