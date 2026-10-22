import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base=(process.env.TEST_BASE||'').replace(/\/$/,'');
if(!base.startsWith('https://'))throw Error('Set TEST_BASE to the HTTPS deployment URL');
const audio=(await readFile('public/sample-command.wav')).toString('base64');
const ids=process.argv.slice(2);if(!ids.length)ids.push('minicpm-o45','step-audio2-mini');
const checks=[];await mkdir('.runtime',{recursive:true});
for(const id of ids){
 const s=await(await fetch(base+'/api/session',{method:'POST'})).json();
 const start=performance.now();const endpoint=id==='minicpm-o45'?'minicpm-control':'audio-control';
 const response=await fetch(base+'/api/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':s.id,Origin:base},body:JSON.stringify({audio,audioModelId:id,ttsProvider:'supertonic',promptVersion:'compact-v2',inputMode:'file'}),signal:AbortSignal.timeout(420000)});
 assert.equal(response.status,200);let buffer='',metrics,error,bytes=0,heartbeats=0;const decoder=new TextDecoder();
 for await(const chunk of response.body){buffer+=decoder.decode(chunk,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);if(block.startsWith(':')){heartbeats++;continue;}const event=block.match(/^event: (.*)/m)?.[1],data=JSON.parse(block.match(/^data: (.*)/m)?.[1]||'{}');if(event==='audio')bytes+=Buffer.from(data.audio,'base64').length;if(event==='done')metrics=data.metrics;if(event==='error')error=data;}}
 const passed=!error&&metrics?.state?.temperature?.passenger===25&&metrics?.vehicleTools===true&&metrics?.ttsModel==='Supertone/supertonic-3'&&bytes>1000;
 checks.push({model:id,passed,heard:metrics?.input,actions:metrics?.actions,ttsModel:metrics?.ttsModel,audioBytes:bytes,heartbeats,totalMs:Math.round(performance.now()-start),error});
 await writeFile('.runtime/cloud-audio-paths-validation.json',JSON.stringify({base,at:new Date().toISOString(),checks},null,2));console.log(JSON.stringify(checks.at(-1)));assert.ok(passed,JSON.stringify(error||checks.at(-1)));
}
