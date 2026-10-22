import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
test('STT preview routes exact pinned models, rejects mismatch, and preserves vehicle state',async t=>{
 let mismatch=false;const calls=[];
 const worker=http.createServer(async(req,res)=>{
  let body='';for await(const chunk of req)body+=chunk.toString();
  calls.push({url:req.url,body});
  const large=body.includes('qwen3-asr-17b');
  const model=req.url==='/speech/asr'?'Qwen/Qwen3-ASR-'+(large?'1.7B':'0.6B'):req.url==='/whisper/asr'?'openai/whisper-large-v3-turbo':'nvidia/nemotron-3.5-asr-streaming-0.6b';
  res.setHeader('Content-Type','application/json');
  res.end(JSON.stringify({text:'조수석 온도 25도',model:mismatch?'wrong/model':model,revision:large?'7278e1e70fe206f11671096ffdd38061171dd6e5':'5eb144179a02acc5e5ba31e748d22b0cf3e303b0',elapsedMs:7}));
 });worker.listen(0,'127.0.0.1');await once(worker,'listening');
 t.after(()=>{worker.closeAllConnections();worker.close();});
 const url='http://127.0.0.1:'+worker.address().port;
 const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:'18988',CORE_URL:url+'/core',WHISPER_URL:url+'/whisper',SPEECH_URL:url+'/speech'},stdio:['ignore','pipe','pipe']});
 t.after(()=>child.kill());await Promise.race([once(child.stdout,'data'),once(child,'exit').then(()=>{throw Error('Server exited');})]);
 const base='http://127.0.0.1:18988/api/',s=await(await fetch(base+'session',{method:'POST'})).json();
 const headers={'Content-Type':'application/json','X-Session-Id':s.id};
 const send=id=>fetch(base+'asr/transcribe',{method:'POST',headers,body:JSON.stringify({asrId:id,audio:'UklGRg=='})});
 for(const id of ['whisper','nemotron','qwen3-asr-06b','qwen3-asr-17b']){
  const r=await send(id);assert.equal(r.status,200);const data=await r.json();assert.equal(data.asrId,id);assert.equal(data.vehicleStateChanged,false);
  assert.equal(calls.at(-1).url,id.startsWith('qwen')?'/speech/asr':id==='whisper'?'/whisper/asr':'/core/asr');
  if(id.startsWith('qwen'))assert.ok(calls.at(-1).body.includes(id));
 }
 const count=calls.length;assert.equal((await send('__proto__')).status,400);assert.equal(calls.length,count);
 mismatch=true;assert.equal((await send('qwen3-asr-17b')).status,502);
 const exported=await(await fetch(base+'export',{headers})).json();assert.deepEqual(exported.state,s.state);assert.equal(exported.turns.length,0);
});
