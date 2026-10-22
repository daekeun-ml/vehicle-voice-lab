import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';

test('TTS selection reaches the exact worker; invalid names, mismatches, and cancellation cannot silently switch voices',async t=>{
  const calls=[];let mismatch=false,slow=false;
  const wave=Buffer.alloc(2044);wave.write('RIFF');wave.write('WAVE',8);
  const worker=http.createServer(async(req,res)=>{
    for await(const chunk of req){}calls.push(req.url);
    if(req.url==='/core/plan'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({text:JSON.stringify({intent:'control',actions:[{type:'temperature',zone:'passenger',value:25}],reply:''}),elapsedMs:1}));}
    const ppaso=req.url.startsWith('/ppaso'),qwen=req.url.startsWith('/qwen17'),model=ppaso?'akamotaco/ppaso-tts-v1':qwen?'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice':'Supertone/supertonic-3';
    if(req.url.endsWith('/health')){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({ready:true,model}));}
    res.setHeader('Content-Type','audio/wav');res.setHeader('X-Model',mismatch?'wrong/model':model);
    res.setHeader('X-Model-Revision',ppaso?'53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9':qwen?'0c0e3051f131929182e2c023b9537f8b1c68adfe':'3cadd1ee6394adea1bd021217a0e650ede09a323');res.setHeader('X-Voice',ppaso?'single-female':qwen?'Sohee':'F1');
    res.setHeader('X-Sample-Rate',ppaso?'22050':qwen?'24000':'44100');res.setHeader('X-Inference-Ms','2');
    if(slow)setTimeout(()=>res.end(wave),500);else res.end(wave);
  });worker.listen(0,'127.0.0.1');await once(worker,'listening');t.after(()=>{worker.closeAllConnections();worker.close();});
  const url='http://127.0.0.1:'+worker.address().port;
  const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:'18987',BENCHMARK_FIXTURE_KEY:'test-fixture-key',CORE_URL:url+'/core',TTS_URL:url+'/legacy',QWEN17_TTS_URL:url+'/qwen17',SUPERTONIC_TTS_URL:url+'/supertonic',PPASO_TTS_URL:url+'/ppaso'},stdio:['ignore','pipe','pipe']});
  t.after(()=>child.kill());await Promise.race([once(child.stdout,'data'),once(child,'exit').then(()=>{throw Error('Server exited');})]);
  const base='http://127.0.0.1:18987/api/';
  const session=async()=>await(await fetch(base+'session',{method:'POST'})).json();
  const headers=s=>({'Content-Type':'application/json','X-Session-Id':s.id});
  const turn=(s,ttsProvider)=>fetch(base+'turn',{method:'POST',headers:headers(s),body:JSON.stringify({text:'조수석 25도로',ttsProvider})});
  const state=async s=>(await(await fetch(base+'export',{headers:headers(s)})).json()).state;
  for(const id of ['qwen17','supertonic','ppaso']){
    const s=await session(),r=await turn(s,id),body=await r.text();
    assert.equal(r.status,200);assert.ok(calls.includes('/'+id+'/tts'));assert.match(body,/event: audio/);
    const done=body.split('\n\n').find(x=>x.startsWith('event: done'));
    const metrics=JSON.parse(done.split('\ndata: ')[1]).metrics;
    assert.equal(metrics.ttsProvider,id);assert.equal(metrics.ttsModel,id==='ppaso'?'akamotaco/ppaso-tts-v1':id==='qwen17'?'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice':'Supertone/supertonic-3');
    assert.equal(metrics.ttsSampleRate,id==='ppaso'?22050:id==='qwen17'?24000:44100);assert.equal((await state(s)).temperature.passenger,25);
  }
  let s=await session(),count=calls.length,r=await turn(s,'typo');assert.equal(r.status,400);assert.equal(calls.length,count);assert.equal((await state(s)).revision,0);
  mismatch=true;s=await session();let body=await(await turn(s,'qwen17')).text();assert.match(body,/event: error/);assert.doesNotMatch(body,/event: audio/);assert.equal((await state(s)).temperature.passenger,25);mismatch=false;
  slow=true;s=await session();r=await turn(s,'supertonic');const reader=r.body.getReader(),decoder=new TextDecoder();body='';let canceled=false;
  for(;;){const {done,value}=await reader.read();if(done)break;body+=decoder.decode(value);if(!canceled&&body.includes('event: reply')){canceled=true;await fetch(base+'cancel',{method:'POST',headers:headers(s),body:'{}'});}}
  assert.ok(canceled);assert.doesNotMatch(body,/event: audio/);assert.equal((await state(s)).temperature.passenger,25);
  const providers=await(await fetch(base+'tts')).json();assert.ok(providers.providers.some(p=>p.id==='supertonic'&&p.ready));assert.ok(providers.providers.every(p=>!Object.hasOwn(p,'url')));
  slow=false;s=await session();
  let seeded=await fetch(base+'benchmark/fixture',{method:'POST',headers:headers(s),body:JSON.stringify({caseId:'context-04'})});assert.equal(seeded.status,403);
  seeded=await fetch(base+'benchmark/fixture',{method:'POST',headers:{...headers(s),'X-Benchmark-Key':'test-fixture-key'},body:JSON.stringify({caseId:'context-04'})});
  assert.equal(seeded.status,200);const seed=await seeded.json();assert.equal(seed.state.temperature.driver,26);assert.equal(seed.state.temperature.passenger,23);assert.equal(seed.fixtureSha256.length,64);
  const before=await state(s),planningCalls=calls.filter(x=>x==='/core/plan').length;
  const preview=await fetch(base+'tts/preview',{method:'POST',headers:headers(s),body:JSON.stringify({ttsProvider:'supertonic',text:'운전석을 30도로 맞춰줘.'})});
  assert.equal(preview.status,200);const voice=await preview.json();assert.equal(voice.vehicleStateChanged,false);assert.equal(voice.model,'Supertone/supertonic-3');
  assert.deepEqual(await state(s),before);assert.equal(calls.filter(x=>x==='/core/plan').length,planningCalls);
  assert.equal((await fetch(base+'session',{method:'DELETE',headers:headers(s)})).status,200);
  assert.equal((await fetch(base+'export',{headers:headers(s)})).status,400);
});
