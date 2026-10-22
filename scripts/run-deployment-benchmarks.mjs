// Run fixed audio suites against an isolated instance of the deployed application.
// Only the private benchmark backend enables predefined fixture injection.
import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import WebSocket from 'ws';
import {initialState,executePlan} from '../vehicle.mjs';
import {cases as originalCases,variants} from './vehicle-benchmark-cases.mjs';

const base=(process.env.BENCH_BASE||'http://127.0.0.1:8788').replace(/\/$/,'');
const root='research/deployment-benchmarks';
const catalog=JSON.parse(await readFile('model-catalog.json','utf8'));
const hardBytes=await readFile('research/vehicle-hard-v1/cases.json');
const hard=JSON.parse(hardBytes);const fixtureHash=createHash('sha256').update(hardBytes).digest('hex');
const key=(await readFile(process.env.BENCH_KEY_FILE||'.runtime/benchmark-fixture.key','utf8')).trim();
const allModels=catalog.models.filter(m=>m.status==='ready'&&(m.role==='sllm'||m.audioPlanner||['sonic','minicpm-o45'].includes(m.id)));
if(allModels.length!==14)throw Error('Expected the reviewed 14 control configurations');
const requested=process.argv.slice(2);const selected=allModels.filter(m=>!requested.length||requested.includes(m.id));
const order=['qwen35-4b-nf4','qwen35-4b','gemma4-e2b','phi4-mini','qwen35-2b','qwen35-08b','smollm3','exaone4-12b','hyperclova-05b','minicpm-o45','step-audio2-mini','mimo-audio','qwen3-omni','sonic'];
selected.sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id));
const suites=[['original31',variants,'output/vehicle-benchmark'],['hard48',hard.cases,'output/vehicle-hard-v1']];
const audioHashes={};
for(const [name,rows,folder] of suites){
 const items=[];for(const c of rows){const b=await readFile(`${folder}/${c.id}.wav`);items.push([c.id,createHash('sha256').update(b).digest('hex')]);}
 audioHashes[name]=createHash('sha256').update(JSON.stringify(items)).digest('hex');
 await mkdir(`${root}/${name}`,{recursive:true});
}
const redact=e=>({error:String(e?.error||e?.message||e).replace(/https?:\/\/\S+/g,'[remote URL]').slice(0,600),failureStage:e?.failureStage||'transport'});
const canonical=(actions,ordered=false)=>{
 if(!Array.isArray(actions))return null;
 const rows=actions.flatMap(a=>a?.type==='temperature'&&a.zone==='both'?[{...a,zone:'driver'},{...a,zone:'passenger'}]:[a]).map(a=>JSON.stringify(Object.fromEntries(Object.entries(a||{}).sort())));
 return JSON.stringify(ordered?rows:rows.sort());
};
const stateEqual=(a,b,revision=false)=>{if(!a||!b)return false;const normalize=x=>{const y=structuredClone(x);if(!revision)delete y.revision;return JSON.stringify(y);};return normalize(a)===normalize(b);};
const q=(a,p)=>{a=a.filter(Number.isFinite).sort((a,b)=>a-b);return a.length?a[Math.max(0,Math.ceil(a.length*p)-1)]:null;};
async function atomic(file,value){const tmp=file+`.${process.pid}.tmp`;await writeFile(tmp,JSON.stringify(value,null,2));await rename(tmp,file);}
async function json(path,options={}){const r=await fetch(base+path,{...options,signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error(`${path}: HTTP ${r.status}`);return r.json();}
const headers=s=>({'Content-Type':'application/json','X-Session-Id':s.id});
const openSession=()=>json('/api/session',{method:'POST'});
const closeSession=s=>json('/api/session',{method:'DELETE',headers:headers(s)}).catch(()=>{});
async function summary(){
 const models=[];
 for(const m of allModels){const item={id:m.id,name:m.name,role:m.role,repo:m.repo,suites:{}};
  for(const [suite,rows] of suites){let run;try{run=JSON.parse(await readFile(`${root}/${suite}/${m.id}.json`,'utf8'));}catch{}
   const r=run?.rows||[];item.suites[suite]={status:run?.status||'pending',completed:r.length,total:rows.length,
    passed:suite==='original31'?r.filter(x=>x.passed).length:null,
    strictPassed:run?.strictPassed??null,semanticReviewer:run?.semanticReviewCompletedAt?'Codex assistant; not human listening':null,
    actionStateCorrect:r.filter(x=>x.actionStateCorrect).length,modelActionCorrect:r.filter(x=>x.modelActionCorrect===true).length,
    modelActionObserved:r.filter(x=>x.modelActionCorrect!==null&&x.modelActionCorrect!==undefined).length,
    errors:r.filter(x=>x.error).length,semanticReviewPending:suite==='hard48'?r.filter(x=>x.semanticReviewRequired&&!x.semanticReview).length:0,
    startedAt:run?.startedAt,completedAt:run?.completedAt,asrId:run?.asrId,promptVersion:run?.promptVersion,
    medianFirstAudioMs:q(r.filter(x=>!x.modelLoadMs).map(x=>x.firstAudioMs),.5),p95FirstAudioMs:q(r.filter(x=>!x.modelLoadMs).map(x=>x.firstAudioMs),.95),
    blockReason:run?.blockReason};
  }models.push(item);
 }
 const complete=models.every(m=>Object.values(m.suites).every(s=>s.status==='complete'));
 await atomic(`${root}/summary.json`,{updatedAt:new Date().toISOString(),status:complete?'complete':'running',region:'ap-northeast-2',hardware:'g6e.2xlarge / L40S 48GB',sharedWorkers:true,
  suites:[{id:'original31',name:'기존 31개 음성 재평가',total:31,metric:'앱 동작·상태·답변 규칙·음성 출력 통과',input:'동일 25문장 + 다른 합성 목소리 3 + 백색 잡음 20dB 3; 이번에 재생성한 공통 파형'},
          {id:'hard48',name:'고난도 48개 음성',total:48,metric:'동작·상태 일치와 모델 원안 분리; 응답 의미 검토 별도',input:'Polly Seoyeon 합성 음성 + 고정 선행 상태·대화 fixture'}],
  audioCorpusHashes:audioHashes,fixtureHash,releaseSha256:process.env.BENCH_RELEASE_SHA,models,
  timing:'고정 앱 백엔드에서 측정. 모델 워커는 공개 데모와 공유. Sonic은 실제 음성 전송 종료 기준으로 별도 표시. 첫 로딩 포함 행은 지연 집계에서 제외.',
  notes:['기존 저장 점수는 별도 표에 보존합니다.','원본 31개 입력 파형이 저장소에 없어 같은 합성 설정으로 재생성했습니다.','Sonic은 새 연결에 이전 대화를 시스템 문맥 데이터로 전달합니다.','고난도 자동 동작 점수만으로 답변 의미까지 통과했다고 해석하지 않습니다.']});
}
function pcm(wav){let off=12;while(off+8<=wav.length){const n=wav.readUInt32LE(off+4);if(wav.toString('ascii',off,off+4)==='data')return wav.subarray(off+8,off+8+n);off+=8+n+(n%2);}throw Error('WAV data missing');}
async function connectSonic(s){
 const ws=new WebSocket(`${base.replace(/^http/,'ws')}/api/sonic?session=${s.id}&language=ko`,{origin:base});
 await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{ws.close();reject(Error('Sonic connect timeout'));},30000);const onMessage=raw=>{const {event,data}=JSON.parse(raw);if(event==='ready'){clearTimeout(timer);ws.off('message',onMessage);resolve();}if(event==='error'){clearTimeout(timer);ws.close();reject(Error(data.error));}};ws.on('message',onMessage);ws.once('error',e=>{clearTimeout(timer);reject(e);});});return ws;
}
async function sonicTurn(ws,s,bytes){
 const input=pcm(bytes);let offset=0,inputEnd,firstAudio,heard='',reply='',audioBytes=0,doneAt=0,lastVoiceSentAt=Infinity,turns=0;const toolErrors=[];const start=performance.now();
 let lastVoiceByte=0;for(let i=0;i<input.length;i+=2)if(Math.abs(input.readInt16LE(i))>128)lastVoiceByte=i+2;
 await new Promise((resolve,reject)=>{
  let interval;const finish=e=>{clearTimeout(timer);clearInterval(interval);ws.off('message',onMessage);ws.off('error',finish);e?reject(e):resolve();};
  const maybeFinish=()=>{if(inputEnd&&audioBytes&&doneAt>=lastVoiceSentAt)finish();};
  const timer=setTimeout(()=>finish(Error('Sonic turn timeout')),90000);
  const onMessage=raw=>{const{event,data}=JSON.parse(raw);if(event==='text'){if(data.role==='USER')heard+=data.text;else reply+=data.text;}if(event==='audio'){audioBytes+=Buffer.from(data.audio,'base64').length;firstAudio??=performance.now();}if(event==='tool'&&data.toolName==='vehicle_control'&&data.ok===false)toolErrors.push(String(data.error));if(event==='done'){doneAt=performance.now();turns++;maybeFinish();}if(event==='error')finish(Error(data.error));};
  ws.on('message',onMessage);ws.once('error',finish);ws.send(JSON.stringify({type:'mode',mode:'file'}));
  interval=setInterval(()=>{if(ws.readyState!==1)return;if(offset<input.length){ws.send(input.subarray(offset,offset+3200));offset+=3200;if(offset>=lastVoiceByte&&lastVoiceSentAt===Infinity)lastVoiceSentAt=performance.now();if(offset>=input.length){inputEnd=performance.now();maybeFinish();}}else ws.send(Buffer.alloc(3200));},100);
 });
 const data=await json('/api/export',{headers:headers(s)}),metrics=data.turns.at(-1);
 // Aggregate native calls if the streaming turn detector split a long utterance.
 return{metrics:{...metrics,input:heard,reply,state:data.state,actions:data.turns.flatMap(t=>t.actions||[]),modelProposedActions:data.turns.flatMap(t=>t.modelProposedActions||[]),modelPlanMalformed:data.turns.some(t=>t.modelPlanMalformed)},toolErrors,firstAudioMs:firstAudio&&inputEnd?Math.round(firstAudio-inputEnd):null,audioBytes,audioValid:audioBytes>1000,elapsedMs:Math.round(performance.now()-start),nativeTurns:turns};
}
async function turn(model,s,bytes,ws){
 if(model.id==='sonic')return sonicTurn(ws,s,bytes);
 const endpoint=model.role==='sllm'?'turn':model.id==='minicpm-o45'?'minicpm-control':'audio-control';
 const start=performance.now(),r=await fetch(base+'/api/'+endpoint,{method:'POST',headers:headers(s),body:JSON.stringify({audio:bytes.toString('base64'),plannerId:model.id,audioModelId:model.id,ttsProvider:'polly',inputMode:'file',asrId:model.demoConfig?.asrId||'whisper',promptVersion:model.demoConfig?.promptVersion||'compact-v2',generationProfile:'deterministic'}),signal:AbortSignal.timeout(420000)});
 if(!r.ok)throw Error(`HTTP ${r.status}: ${(await r.text()).slice(0,200)}`);
 let buffer='',metrics,error,reply,firstAudioMs,audioBytes=0,audioValid=false;const decoder=new TextDecoder();
 for await(const chunk of r.body){buffer+=decoder.decode(chunk,{stream:true});let i;while((i=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,i);buffer=buffer.slice(i+2);if(block.startsWith(':'))continue;const event=block.match(/^event: (.*)/m)?.[1],data=JSON.parse(block.match(/^data: (.*)/m)?.[1]||'{}');if(event==='audio'){const b=Buffer.from(data.audio,'base64');audioBytes+=b.length;audioValid=b.toString('ascii',0,4)==='RIFF'&&b.length>1000;firstAudioMs??=Math.round(performance.now()-start);}if(event==='reply')reply=data;if(event==='done')metrics=data.metrics;if(event==='error')error=redact(data);}}
 return{metrics,reply,error,firstAudioMs,audioBytes,audioValid,elapsedMs:Math.round(performance.now()-start)};
}
function evaluate(model,suite,c,r,preludeCorrect=true){
 const m=r.metrics||{};let expectedActions,expectedState,ordered=false,alternatives=[];
 if(suite==='original31'){
  let before=initialState(),previous=null;if(c.prelude){const p=originalCases.find(p=>p.id===c.prelude),e=executePlan(before,null,{intent:'control',actions:p.actions,reply:''});before=e.state;previous=e.previous;}
  expectedActions=c.actions;expectedState=executePlan(before,previous,{intent:c.intent||'control',actions:c.actions,reply:''}).state;
 }else{expectedActions=c.expected.actions;expectedState=c.expected.state;ordered=c.expected.orderedActions;alternatives=c.expected.allowedActionAlternatives||[];}
 const accepted=[expectedActions,...alternatives].map(a=>canonical(a,ordered));
 const actionCorrect=accepted.includes(canonical(m.actions,ordered));
 const modelActionCorrect=m.modelPlanMalformed?false:Array.isArray(m.modelProposedActions)?accepted.includes(canonical(m.modelProposedActions,ordered)):null;
 const stateCorrect=stateEqual(m.state,expectedState,suite==='hard48');
 const answerCorrect=suite!=='original31'||!c.answer||/22|이십이|스물두/.test(m.reply||'');
 const intentCorrect=suite!=='original31'||!c.intent||(model.id==='sonic'?/어디|목적지|알려|정해|장소/.test(m.reply||''):m.intent===c.intent||(c.intent==='clarify'&&m.intent==='question'&&/목적지|어디|장소/.test(m.reply||'')));
 const denialCorrect=suite!=='original31'||!c.denial||(/불가|못|않|지원|범위|16|30|없|어려|조절할 수/.test(m.reply||'')&&!/설정했|바꿨|맞췄/.test(m.reply||''));
 const actionStateCorrect=!r.error&&preludeCorrect&&actionCorrect&&stateCorrect;
 return{id:c.id,category:c.category,variant:c.variant,text:suite==='hard48'?c.input.utterance:c.text,
  expectedActions,expectedState,actualActions:m.actions,modelProposedActions:m.modelProposedActions,actualState:m.state,
  heard:m.input,rawTranscript:m.rawTranscript,reply:m.reply,modelReply:m.modelReply,
  preludeCorrect,actionCorrect,stateCorrect,stateIgnoringRevisionCorrect:stateEqual(m.state,expectedState),modelActionCorrect,actionStateCorrect,
  passed:suite==='original31'?actionStateCorrect&&answerCorrect&&intentCorrect&&denialCorrect&&r.audioValid&&!r.toolErrors?.length:null,
  answerCorrect,intentCorrect,denialCorrect,semanticReviewRequired:suite==='hard48'&&c.expected.outcome!=='execute',replyRequirements:c.expected?.replyRequirements,
  audioValid:r.audioValid,audioBytes:r.audioBytes,firstAudioMs:r.firstAudioMs,elapsedMs:r.elapsedMs,modelLoadMs:m.modelLoadMs||0,
  asrMs:m.asrMs,llmMs:m.llmMs,ttsMs:m.ttsMs,quantization:m.quantization,ttsModel:m.ttsModel||(model.id==='sonic'?model.repo:null),
  validationError:m.validationError,guardReason:m.guardReason,error:r.error,nativeTurns:r.nativeTurns,toolErrors:r.toolErrors,
  fixtureHash:suite==='hard48'?fixtureHash:undefined};
}
await summary();
for(const model of selected){
 for(const [suite,cases,folder] of suites){
  const file=`${root}/${suite}/${model.id}.json`;let report;
  try{report=JSON.parse(await readFile(file,'utf8'));if(report.audioCorpusHash!==audioHashes[suite])throw Error('Corpus changed; use a new report directory');}catch(e){if(e.code!=='ENOENT')throw e;}
  const infra=r=>r.error&&['transport','model-planning'].includes(r.error.failureStage);
  if(report?.status==='complete'&&!(process.env.BENCH_RETRY_INFRA==='1'&&report.rows.some(infra)))continue;
  if(report&&process.env.BENCH_RETRY_INFRA==='1'){report.infrastructureAttempts=[...(report.infrastructureAttempts||[]),...report.rows.filter(infra)];report.rows=report.rows.filter(r=>!infra(r));}
  report??={modelId:model.id,name:model.name,repo:model.repo,revision:model.revision,suite,status:'running',startedAt:new Date().toISOString(),
   releaseSha256:process.env.BENCH_RELEASE_SHA,audioCorpusHash:audioHashes[suite],fixtureHash:suite==='hard48'?fixtureHash:undefined,
   asrId:model.role==='sllm'?(model.demoConfig?.asrId||'whisper'):null,promptVersion:model.demoConfig?.promptVersion||'compact-v2',
   generationProfile:model.id==='sonic'?'native temperature 0.3, topP 0.9':'deterministic',quantization:model.quantization||(model.id==='qwen3-omni'?'mixed-nf4':model.id==='sonic'?'managed':'bf16'),
   timingBasis:model.id==='sonic'?'first audio minus complete real-time input transmission':'HTTP submit to first received audio; private backend on Seoul GPU host',rows:[]};
  report.status='running';await atomic(file,report);await summary();
  const completed=new Set(report.rows.map(r=>r.id));
  for(const c of cases){
   if(completed.has(c.id))continue;
   let s,ws,r,preludeCorrect=true;
   try{
    s=await openSession();
    if(suite==='hard48'){
     const seeded=await json('/api/benchmark/fixture',{method:'POST',headers:{...headers(s),'X-Benchmark-Key':key},body:JSON.stringify({caseId:c.id})});
     if(seeded.fixtureSha256!==fixtureHash||!stateEqual(seeded.state,c.input.state,true))throw Error('Fixture mismatch');
    }
    if(model.id==='sonic')ws=await connectSonic(s);
    if(suite==='original31'&&c.prelude){
     const p=originalCases.find(p=>p.id===c.prelude),pre=await turn(model,s,await readFile(`${folder}/${p.id}.wav`),ws);
     const exp=executePlan(initialState(),null,{intent:'control',actions:p.actions,reply:''});
     preludeCorrect=!pre.error&&stateEqual(pre.metrics?.state,exp.state)&&canonical(pre.metrics?.actions)===canonical(p.actions);
    }
    const turnCount=model.id==='sonic'?(await json('/api/export',{headers:headers(s)})).turns.length:0;
    r=await turn(model,s,await readFile(`${folder}/${c.id}.wav`),ws);
    if(model.id==='sonic'&&turnCount){const data=await json('/api/export',{headers:headers(s)});r.metrics.actions=data.turns.slice(turnCount).flatMap(t=>t.actions||[]);r.metrics.modelProposedActions=data.turns.slice(turnCount).flatMap(t=>t.modelProposedActions||[]);}
   }catch(e){r={error:redact(e),audioValid:false,audioBytes:0};}
   finally{ws?.close();if(s)await closeSession(s);}
   const row=evaluate(model,suite,c,r,preludeCorrect);report.rows.push(row);await atomic(file,report);await summary();
   console.log(JSON.stringify({suite,model:model.id,case:c.id,n:report.rows.length,total:cases.length,passed:row.passed,actionState:row.actionStateCorrect,modelAction:row.modelActionCorrect,error:row.error}));
   // Stop a broken environment instead of presenting repeated infrastructure errors as model accuracy.
   if(report.rows.slice(-3).length===3&&report.rows.slice(-3).every(x=>x.error&&['transport','model-planning'].includes(x.error.failureStage))){report.status='blocked';report.blockReason='Three consecutive infrastructure failures; inspect worker logs before resuming';await atomic(file,report);await summary();throw Error(`${model.id}: ${report.blockReason}`);}
  }
  report.status='complete';report.completedAt=new Date().toISOString();await atomic(file,report);await summary();
 }
}
console.log('Selected model runs completed.');
