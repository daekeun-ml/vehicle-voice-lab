import{readFile,writeFile}from'node:fs/promises';
const base=process.env.TEST_BASE;
if(!base?.startsWith('https://'))throw Error('Set TEST_BASE to the deployed HTTPS URL');
const audio=(await readFile('public/sample-command.wav')).toString('base64');
async function json(path,options){const r=await fetch(base+path,options);if(!r.ok)throw Error(`${path}: HTTP ${r.status}: ${(await r.text()).slice(0,150)}`);return r.json();}
const results={at:new Date().toISOString(),base,syntheticInput:true,measurement:'Client HTTP submit to first received audio; excludes browser playback and microphone VAD',checks:[]};
async function turn(session,extra={}){
 const start=performance.now();const r=await fetch(base+(extra.audioModelId?'/api/audio-control':'/api/turn'),{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':session.id,Origin:base},body:JSON.stringify({audio,plannerId:'qwen35-4b-nf4',asrId:'whisper',promptVersion:'compact-v2',ttsProvider:'polly',inputMode:'file',...extra}),signal:AbortSignal.timeout(360000)});
 if(!r.ok)throw Error(`Turn HTTP ${r.status}: ${(await r.text()).slice(0,150)}`);
 const decoder=new TextDecoder();let buffer='',firstAudioMs,heartbeats=0,metrics,error,audioBytes=0;
 for await(const chunk of r.body){buffer+=decoder.decode(chunk,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,end);buffer=buffer.slice(end+2);if(block.startsWith(':')){heartbeats++;continue;}const event=block.match(/^event: (.*)/m)?.[1],data=JSON.parse(block.match(/^data: (.*)/m)?.[1]||'{}');if(event==='audio'){firstAudioMs??=Math.round(performance.now()-start);audioBytes+=Buffer.from(data.audio||'','base64').length;}if(event==='done')metrics=data.metrics;if(event==='error')error=data;}}
 const result={model:extra.audioModelId||'qwen35-4b-nf4',passed:!!firstAudioMs&&metrics?.state?.temperature?.passenger===25,firstAudioMs,totalMs:Math.round(performance.now()-start),heartbeats,audioBytes,asrMs:metrics?.asrMs,llmMs:metrics?.llmMs,ttsMs:metrics?.ttsMs,modelLoadMs:metrics?.modelLoadMs,quantization:metrics?.quantization,passenger:metrics?.state?.temperature?.passenger,error};
 results.checks.push(result);console.log(JSON.stringify(result));await writeFile('research/cloud-deployment-validation.json',JSON.stringify(results,null,2));if(!result.passed)throw Error('Voice control failed');
}
const health=await json('/api/health'),catalog=await json('/api/catalog'),benchmark=await json('/api/benchmark');
results.health={ready:health.ready,deployment:health.deployment,region:health.region,speechReady:health.researchWorkers?.speech?.ready};results.catalog={count:catalog.models.length,default:catalog.defaultPlannerId};results.benchmark={status:benchmark.status,completedModels:benchmark.completedModels};
for(const path of['/','/app.js','/sample-command.wav','/api/benchmark-csv','/api/benchmark-audio/qwen35-4b-nf4/passenger-25']){const r=await fetch(base+path);if(!r.ok)throw Error(`Asset ${path} HTTP ${r.status}`);await r.arrayBuffer();}
results.assetsPassed=true;
const session=await json('/api/session',{method:'POST'}),other=await json('/api/session',{method:'POST'});
for(let i=0;i<3;i++)await turn(session);
const exportOther=await json('/api/export',{headers:{'X-Session-Id':other.id}});
results.sessionIsolation=exportOther.state.temperature.passenger===other.state.temperature.passenger&&exportOther.turns.length===0;
if(!results.sessionIsolation)throw Error('Session state leaked');
if(process.env.TEST_LONG_SSE==='1')await turn(session,{audioModelId:'qwen3-omni'});
results.passed=true;await writeFile('research/cloud-deployment-validation.json',JSON.stringify(results,null,2));console.log(JSON.stringify({passed:true,assets:true,sessionIsolation:results.sessionIsolation}));
