import {readFile,writeFile} from 'node:fs/promises';
const audio=(await readFile('public/sample-command.wav')).toString('base64'),rows=[];
for(const plannerId of ['gemma4-e2b','hyperclova-05b','exaone4-12b','smollm3']){
 const session=await(await fetch('http://localhost:8787/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
 const r=await fetch('http://localhost:8787/api/turn',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':session.id},body:JSON.stringify({plannerId,audio,inputMode:'file',ttsProvider:'polly'}),signal:AbortSignal.timeout(180000)});
 const blocks=(await r.text()).split('\n\n').filter(Boolean).map(block=>({event:block.match(/^event: (.*)/m)?.[1],data:JSON.parse(block.match(/^data: (.*)/m)?.[1]||'{}')}));
 const result=blocks.find(b=>b.event==='reply')?.data,metrics=blocks.find(b=>b.event==='done')?.data.metrics,error=blocks.find(b=>b.event==='error')?.data.error;
 const row={plannerId,transcript:blocks.find(b=>b.event==='transcript')?.data.text,planner:metrics?.planner,revision:metrics?.plannerRevision,actions:result?.actions,reply:result?.reply,state:result?.state,asrMs:metrics?.asrMs,llmMs:metrics?.llmMs,loadMs:metrics?.modelLoadMs,ttsProvider:metrics?.ttsProvider,ttsMs:metrics?.ttsMs,audioReceived:blocks.some(b=>b.event==='audio'&&b.data.audio?.length>1000),commandCorrect:result?.state?.temperature?.passenger===25&&result?.state?.temperature?.driver===22,error};rows.push(row);console.log(JSON.stringify(row));
}
await writeFile('research/planner-audio-integration.json',JSON.stringify({at:new Date().toISOString(),input:'Synthetic Korean passenger-25 WAV; not human microphone',rows},null,2));
