// Paired ASR comparison. Control replay uses one fixed planner and preserved fixtures.
import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {initialState,executePlan} from '../vehicle.mjs';
import {normalizeTranscript} from '../transcript.mjs';
import {variants,cases} from './vehicle-benchmark-cases.mjs';
const base=process.env.ASR_BENCH_BASE||'http://127.0.0.1:8789',root='research/asr-comparison';
const manifestBytes=await readFile('output/asr-comparison/manifest.json'),manifest=JSON.parse(manifestBytes);
const hard=JSON.parse(await readFile('research/vehicle-hard-v1/cases.json'));
const fixtureKey=(await readFile('.runtime/benchmark-fixture.key','utf8')).trim();
const models=process.argv.slice(2).length?process.argv.slice(2):['whisper','nemotron','qwen3-asr-06b','qwen3-asr-17b'];
const allModels=['whisper','nemotron','qwen3-asr-06b','qwen3-asr-17b'];
const planner={plannerId:'qwen35-4b',promptVersion:'compact-v2',generationProfile:'deterministic',ttsProvider:'polly'};
const corpusHash=createHash('sha256').update(manifestBytes).digest('hex');
await mkdir(root,{recursive:true});
async function atomic(path,value){await writeFile(path+'.tmp',JSON.stringify(value,null,2));await rename(path+'.tmp',path);}
async function request(path,session,body,extra={}){
 const r=await fetch(base+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(session?{'X-Session-Id':session.id}:{}),...extra},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(240000)});
 if(!r.ok)throw Error(`${path} HTTP ${r.status}: ${(await r.text()).slice(0,200)}`);return r;
}
const norm=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
function edit(a,b){let p=Array.from({length:b.length+1},(_,i)=>i);for(let i=1;i<=a.length;i++){const n=[i];for(let j=1;j<=b.length;j++)n[j]=Math.min(n[j-1]+1,p[j]+1,p[j-1]+(a[i-1]===b[j-1]?0:1));p=n;}return p[b.length];}
const canonical=a=>JSON.stringify((a||[]).flatMap(x=>x.type==='temperature'&&x.zone==='both'?[{...x,zone:'driver'},{...x,zone:'passenger'}]:[x]).map(x=>JSON.stringify(Object.fromEntries(Object.entries(x).sort()))).sort());
const numeric=s=>normalizeTranscript(s.replace(/스물네|스물넷/g,'24').replace(/스물일곱/g,'27').replace(/스물다섯/g,'25').replace(/스물두/g,'22').replace(/스물세/g,'23').replace(/스물한/g,'21')).match(/\d+(?:\.\d+)?/g)||[];
function entities(reference,heard){
 return Object.fromEntries([['numbers',numeric(reference),numeric(heard)],['seats',reference.match(/운전석|조수석|양쪽/g)||[],heard.match(/운전석|조수석|양쪽/g)||[]],['destinations',reference.match(/서울역|서울숲/g)||[],heard.match(/서울역|서울숲/g)||[]]].map(([k,a,b])=>[k,{eligible:a.length>0,correct:JSON.stringify(a)===JSON.stringify(b),expected:a,heard:b}]));
}
async function turn(s,text){
 const r=await request('/api/turn',s,{...planner,text:normalizeTranscript(text)});const content=await r.text();
 const blocks=content.split('\n\n'),err=blocks.find(x=>x.startsWith('event: error'));
 if(err)throw Error(JSON.parse(err.split('\ndata: ')[1]).error);
 const done=blocks.find(x=>x.startsWith('event: done'));if(!done)throw Error('No completed control turn');
 return JSON.parse(done.split('\ndata: ')[1]).metrics;
}
async function control(s,item,text){
 let expected,expectedActions,alternatives=[],ordered=false;
 if(item.suite==='hard48'){
  const c=hard.cases.find(x=>x.id===item.caseId);
  await request('/api/benchmark/fixture',s,{caseId:c.id},{'X-Benchmark-Key':fixtureKey});
  expected=c.expected.state;expectedActions=c.expected.actions;alternatives=c.expected.allowedActionAlternatives||[];ordered=c.expected.orderedActions;
 }else{
  const c=variants.find(x=>x.id===item.caseId);let before=initialState(),previous=null;
  if(c.prelude){const p=cases.find(x=>x.id===c.prelude),e=executePlan(before,null,{intent:'control',actions:p.actions,reply:''});
   const pre=await turn(s,p.text);if(canonical(pre.actions)!==canonical(p.actions))throw Error('Fixed text prelude failed');before=e.state;previous=e.previous;}
  expected=executePlan(before,previous,{intent:c.intent||'control',actions:c.actions,reply:''}).state;expectedActions=c.actions;
 }
 if(!text.trim())return {actionStateCorrect:false,error:'Empty ASR transcript',recognitionEmpty:true};
 const m=await turn(s,text);
 const actualState=structuredClone(m.state),exp=structuredClone(expected);
 if(item.suite==='original31'){delete actualState.revision;delete exp.revision;}
 const encode=a=>ordered?JSON.stringify(a):canonical(a);
 const actionCorrect=[expectedActions,...alternatives].some(a=>encode(a)===encode(m.actions));
 return {actionStateCorrect:actionCorrect&&JSON.stringify(actualState)===JSON.stringify(exp),actionCorrect,actualActions:m.actions,expectedActions,actualState:m.state,expectedState:expected,reply:m.reply,llmMs:m.llmMs};
}
const median=a=>{a=a.filter(Number.isFinite).sort((a,b)=>a-b);return a.length?a[Math.floor(a.length/2)]:null;};
async function summary(){
 const results=[];
 for(const id of allModels){
  let run;try{run=JSON.parse(await readFile(`${root}/${id}.json`));}catch{run={rows:[],status:'pending'};}
  const groups=[];
  for(const condition of [...new Set(manifest.items.map(x=>x.condition))]){
   const rows=run.rows.filter(r=>r.condition===condition),ok=rows.filter(r=>!r.error);
   const chars=ok.reduce((a,r)=>a+r.referenceCharacters,0);
   groups.push({condition,completed:rows.length,total:manifest.items.filter(x=>x.condition===condition).length,errors:rows.filter(r=>r.error).length,
    cer:chars?ok.reduce((a,r)=>a+r.characterErrors,0)/chars:null,exact:ok.filter(r=>r.characterErrors===0).length,
    actionStateCorrect:ok.filter(r=>r.control?.actionStateCorrect).length,medianAsrMs:median(ok.filter(r=>!r.loadMs).map(r=>r.asrMs)),
    medianRtf:median(ok.filter(r=>!r.loadMs).map(r=>r.asrMs/(r.durationSeconds*1000))),
    entities:Object.fromEntries(['numbers','seats','destinations'].map(k=>[k,{correct:ok.filter(r=>r.entities[k].eligible&&r.entities[k].correct).length,total:ok.filter(r=>r.entities[k].eligible).length}]))});
  }results.push({id,status:run.status,completed:run.rows.length,total:manifest.items.length,groups});
 }
 await atomic(root+'/summary.json',{updatedAt:new Date().toISOString(),status:results.every(x=>x.status==='complete')?'complete':'running',corpusHash,planner,
  metrics:'CER removes punctuation/whitespace, keeps numeric spelling. Entity metric compares explicit ordered mentions; control is action/state only, not reply semantics.',
  timing:'ASR worker elapsed time; model load excluded. Single requests, shared GPUs. Whisper/Nemotron GPU1; Qwen ASR GPU2. Same g6e.2xlarge L40S.',
  synthetic:true,realCarNoise:false,models:results});
}
for(const id of models){
 const path=`${root}/${id}.json`;let run;
 try{run=JSON.parse(await readFile(path));if(run.corpusHash!==corpusHash)throw Error('Corpus changed');}
 catch(e){if(e.code!=='ENOENT')throw e;run={modelId:id,corpusHash,planner,startedAt:new Date().toISOString(),rows:[]};}
 run.status='running';
 if(id.startsWith('qwen3-asr-')){
  // A separate first-time Omni cache build can hold GPU2; do not score that as an ASR failure.
  const deadline=Date.now()+35*60*1000;
  for(;;){
   const health=await(await request('/api/health')).json();
   if(health.researchWorkers?.speech?.independentAsr||!health.researchWorkers?.speech?.loading)break;
   if(Date.now()>deadline)throw Error('GPU2 readiness wait exceeded 35 minutes');
   console.log(JSON.stringify({model:id,status:'waiting-for-gpu2',loading:health.researchWorkers.speech.loading}));
   await new Promise(resolve=>setTimeout(resolve,15000));
  }
 }
 // Warm each model separately; load time isn't reported as steady-state recognition latency.
 const warm=await(await request('/api/session',null,{})).json();
 try{await request('/api/asr/transcribe',warm,{asrId:id,audio:(await readFile(manifest.items[0].file)).toString('base64')});}
 finally{await fetch(base+'/api/session',{method:'DELETE',headers:{'X-Session-Id':warm.id}});}
 for(const item of manifest.items){
  if(run.rows.some(x=>x.id===item.id))continue;
  const s=await(await request('/api/session',null,{})).json();let row={...item};delete row.file;
  try{
   const data=await(await request('/api/asr/transcribe',s,{asrId:id,audio:(await readFile(item.file)).toString('base64')})).json();
   const a=norm(item.text),b=norm(data.text);
   Object.assign(row,{heard:data.text,model:data.model,revision:data.revision,asrMs:data.elapsedMs,requestMs:data.requestMs,loadMs:data.loadMs||0,
    characterErrors:edit(a,b),referenceCharacters:a.length,entities:entities(item.text,data.text)});
   row.control=await control(s,item,data.text);
  }catch(e){row.error=String(e.message).slice(0,600);}
  finally{await fetch(base+'/api/session',{method:'DELETE',headers:{'X-Session-Id':s.id}});}
  run.rows.push(row);await atomic(path,run);await summary();
  console.log(JSON.stringify({model:id,n:run.rows.length,total:manifest.items.length,id:item.id,error:row.error,asrMs:row.asrMs,control:row.control?.actionStateCorrect}));
  if(run.rows.slice(-3).length===3&&run.rows.slice(-3).every(x=>x.error)){run.status='blocked';await atomic(path,run);await summary();throw Error('Three consecutive failures; inspect before retry');}
 }
 run.status='complete';run.completedAt=new Date().toISOString();await atomic(path,run);await summary();
}
