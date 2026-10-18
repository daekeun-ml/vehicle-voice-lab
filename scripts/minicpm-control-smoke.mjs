import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base='http://localhost:8787',s=await(await fetch(base+'/api/session',{method:'POST'})).json();
let current=s;const headers=()=>({'Content-Type':'application/json','X-Session-Id':current.id});const results=[];
const cases=[
  ['defrost-on',state=>state.defrost===true],
  ['temperature-up',(state,turn)=>state.temperature.driver===22&&state.temperature.passenger===22&&!!turn.guardReason&&turn.actions.length===0],
  ['driver-24',state=>state.temperature.driver===24&&state.temperature.passenger===22],
  ['defrost-off',(state,turn)=>state.defrost===false&&turn.actions.some(a=>a.type==='defrost'&&a.value===false)],
];
for(const[file,check]of cases){
  if(['temperature-up','driver-24'].includes(file))current=await(await fetch(base+'/api/session',{method:'POST'})).json();
  const started=performance.now();let row={file};
  try{
    const audio=await readFile('output/minicpm-audit/'+file+'.wav');
    const response=await fetch(base+'/api/minicpm-control',{method:'POST',headers:headers(),body:JSON.stringify({audio:audio.toString('base64'),ttsProvider:'polly',speak:file==='defrost-on',inputMode:'file'}),signal:AbortSignal.timeout(120000)});
    if(!response.ok)throw new Error(await response.text());
    const events=(await response.text()).split('\n\n').filter(Boolean).map(block=>({event:block.split('\n')[0].slice(7),data:JSON.parse(block.split('\n')[1].slice(6))}));
    const error=events.find(e=>e.event==='error');if(error)throw new Error(error.data.error);
    const done=events.find(e=>e.event==='done')?.data.metrics;
    if(!done||done.planner!=='openbmb/MiniCPM-o-4_5')throw new Error('Missing actual MiniCPM planner result');
    if(file==='defrost-on'&&!events.some(e=>e.event==='audio'))throw new Error('Missing Korean speech confirmation');
    Object.assign(row,{passed:check(done.state,done),heard:done.input,guardReason:done.guardReason,reply:done.reply,actions:done.actions,state:done.state,plannerPasses:done.plannerPasses,llmMs:done.llmMs,elapsedMs:Math.round(performance.now()-started)});
  }catch(error){Object.assign(row,{passed:false,error:error.message});}
  results.push(row);console.log(JSON.stringify(row));
}
await mkdir('output',{recursive:true});await writeFile('output/minicpm-control-smoke.json',JSON.stringify({at:new Date().toISOString(),syntheticAudioOnly:true,scenario:'Relative temperature must ask for a target without mutation; absolute temperature uses a fresh session; defrost action values are checked',pipeline:'MiniCPM audio-to-plan -> validated simulator -> Polly Korean TTS',results},null,2));
if(results.some(r=>!r.passed))process.exitCode=1;
