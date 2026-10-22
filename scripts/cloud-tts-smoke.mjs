// Validate provider identity and actual WAV output through the shared HTTPS application.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base=(process.env.TEST_BASE||'').replace(/\/$/,'');
if(!base.startsWith('https://'))throw Error('Set TEST_BASE to the HTTPS deployment URL');
const providers=(process.env.TEST_TTS_PROVIDERS||'polly,qwen,qwen17,supertonic').split(',');
const expected={polly:'Amazon Polly',qwen:'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',qwen17:'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',supertonic:'Supertone/supertonic-3'};
const rates={polly:16000,qwen:24000,qwen17:24000,supertonic:44100};
const sample=(await readFile('public/sample-command.wav')).toString('base64');
const report={at:new Date().toISOString(),base,checks:[],passed:false};
await mkdir('.runtime',{recursive:true});
async function json(path,options={}){const r=await fetch(base+path,options);assert.ok(r.ok,`${path}: ${r.status}`);return r.json();}
async function turn(s,provider,payload){
 const started=performance.now();const response=await fetch(base+'/api/turn',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':s.id,Origin:base},body:JSON.stringify({plannerId:'qwen35-4b-nf4',asrId:'whisper',ttsProvider:provider,...payload}),signal:AbortSignal.timeout(240000)});
 assert.equal(response.status,200);let buffer='',metrics,error,firstAudioMs,bytes=0,validWav=true;const audioChunks=[];const decoder=new TextDecoder();
 for await(const chunk of response.body){buffer+=decoder.decode(chunk,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);if(block.startsWith(':'))continue;const type=block.match(/^event: (.*)/m)?.[1],data=JSON.parse(block.match(/^data: (.*)/m)?.[1]||'{}');
  if(type==='audio'){const audio=Buffer.from(data.audio,'base64');bytes+=audio.length;audioChunks.push(audio);validWav&&=audio.toString('ascii',0,4)==='RIFF'&&audio.toString('ascii',8,12)==='WAVE'&&audio.length>1000;assert.equal(audio.readUInt32LE(24),rates[provider],'WAV sample rate');firstAudioMs??=Math.round(performance.now()-started);}
  if(type==='done')metrics=data.metrics;if(type==='error')error=data;
 }}
 assert.ok(!error,JSON.stringify(error));assert.ok(metrics&&bytes&&validWav,'Missing valid WAV/done event');
 assert.equal(metrics.ttsProvider,provider);assert.equal(metrics.ttsModel,expected[provider]);
 return {metrics,audioBytes:bytes,firstAudioMs,audioChunks};
}
const health=await json('/api/tts');report.providers=health.providers.map(({id,model,ready})=>({id,model,ready}));
for(const provider of providers){
 assert.ok(Object.hasOwn(expected,provider));
 const s=await json('/api/session',{method:'POST'});
 for(const [kind,input,target] of [['text',{text:'조수석 온도를 25도로 맞춰줘.'},25],['audio',{audio:sample,inputMode:'file'},25],['reject',{text:'조수석 온도를 40도로 설정해줘.'},25]]){
  const r=await turn(s,provider,input);assert.equal(r.metrics.state.temperature.passenger,target);
  if(kind==='reject'){assert.deepEqual(r.metrics.actions,[]);assert.match(r.metrics.reply,/범위|16|30|못|않|불가/);}
  await mkdir('.runtime/cloud-tts-audio',{recursive:true});for(let i=0;i<r.audioChunks.length;i++)await writeFile(`.runtime/cloud-tts-audio/${provider}-${kind}-${i}.wav`,r.audioChunks[i]);
  report.checks.push({provider,kind,expectedSpeech:r.metrics.reply,audioFiles:r.audioChunks.map((_,i)=>`.runtime/cloud-tts-audio/${provider}-${kind}-${i}.wav`),passed:true,model:r.metrics.ttsModel,revision:r.metrics.ttsRevision,voice:r.metrics.ttsVoice,sampleRate:r.metrics.ttsSampleRate,firstAudioMs:r.firstAudioMs,ttsMs:r.metrics.ttsMs,audioBytes:r.audioBytes});
  await writeFile('.runtime/cloud-tts-validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report.checks.at(-1)));
 }
}
report.passed=true;await writeFile('.runtime/cloud-tts-validation.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({passed:true,checks:report.checks.length}));
