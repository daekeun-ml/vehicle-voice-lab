import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
await mkdir('output',{recursive:true});

// Uses only checked-in synthetic audio, never a person's recording.
const korean=process.argv.includes('--korean'),base='http://localhost:8787';
const session=await(await fetch(base+'/api/session',{method:'POST'})).json();
const headers={'Content-Type':'application/json','X-Session-Id':session.id};
const unknown=await fetch(base+'/api/turn',{method:'POST',headers,body:JSON.stringify({text:'test',plannerId:'unreviewed-model'})});
assert.equal(unknown.status,400,'Unreviewed planners must be rejected');
const audio=await readFile(korean?'public/sample-command.wav':'public/sample-greeting.wav');
const started=performance.now();
const response=await fetch(base+'/api/s2s',{method:'POST',headers,body:JSON.stringify({comparisonOnly:true,audio:audio.toString('base64'),language:korean?'ko':'en'}),signal:AbortSignal.timeout(120000)});
if(!response.ok)throw new Error(await response.text());
// The response is streamed; retain measurements and text, not base64 audio.
const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',text='',chunks=0,firstAudioMs,done;
while(true){
  const result=await reader.read();if(result.done)break;buffer+=decoder.decode(result.value,{stream:true});let at;
  while((at=buffer.indexOf('\n\n'))!==-1){
    const block=buffer.slice(0,at);buffer=buffer.slice(at+2);
    const event=block.split('\n').find(l=>l.startsWith('event: '))?.slice(7);
    const raw=block.split('\n').find(l=>l.startsWith('data: '))?.slice(6);if(!raw)continue;const data=JSON.parse(raw);
    if(event==='error')throw new Error(data.error);
    if(event==='s2sText')text+=data.text;
    if(event==='audio'){assert.equal(Buffer.from(data.audio,'base64').subarray(0,4).toString(),'RIFF');chunks++;firstAudioMs??=Math.round(performance.now()-started);}
    if(event==='done')done=data.metrics;
  }
}
assert.ok(done?.completed&&chunks>0,'Native speech and turn completion required');
const exported=await(await fetch(base+'/api/export',{headers})).json();
assert.deepEqual(exported.state,session.state,'Research S2S must not mutate the vehicle');
assert.equal(done.vehicleTools,false);
const report={at:new Date().toISOString(),language:korean?'ko':'en',koreanSupported:false,text,chunks,firstAudioMs,totalMs:done.totalMs,model:done.model,revision:done.modelRevision,vehicleUnchanged:true};
await writeFile(`output/minicpm-smoke-${report.language}.json`,JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
