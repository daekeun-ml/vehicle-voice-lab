import{spawn}from'node:child_process';import{readFile,writeFile,mkdir}from'node:fs/promises';
async function run(args,env){await new Promise((resolve,reject)=>{const p=spawn('node',args,{env:{...process.env,BENCH_BASE:'http://localhost:8788/api/',BENCH_ASR:'whisper',...env},stdio:'inherit'});p.once('exit',c=>c===0?resolve():reject(Error('Benchmark exit '+c)));});}
await mkdir('research/vehicle-benchmark-configurations',{recursive:true});
await writeFile('research/vehicle-benchmark-configurations/hyperclova-korean-compact.json',await readFile('research/vehicle-benchmark/hyperclova-05b.json'));
await run(['scripts/vehicle-benchmark.mjs','hyperclova-05b'],{BENCH_PROMPT:'full-v1'});
await run(['scripts/vehicle-benchmark.mjs','qwen35-4b','gemma4-e2b','phi4-mini'],{BENCH_PROMPT:'compact-v2',BENCH_SUITE:'holdout'});
// Leave the final demonstration's selected model warm and verify the new guard
// with actual Korean speech, preserving the original 31-case model scores.
const base='http://localhost:8788/api/',rows=[];
for(const id of['out-of-range','passenger-25','fan-5','defrost-on']){
 const s=await(await fetch(base+'session',{method:'POST'})).json(),audio=await readFile(`output/vehicle-benchmark/${id}.wav`);
 const r=await fetch(base+'turn',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':s.id},body:JSON.stringify({audio:audio.toString('base64'),plannerId:'qwen35-4b',asrId:'whisper',promptVersion:'compact-v2',ttsProvider:'polly',inputMode:'file'})});const raw=await r.text(),events=raw.split('\n\n').filter(Boolean).map(b=>({event:b.match(/^event: (.*)/m)?.[1],data:JSON.parse(b.match(/^data: (.*)/m)?.[1]||'{}')}));const done=events.find(e=>e.event==='done')?.data;rows.push({id,metrics:done?.metrics,reply:events.find(e=>e.event==='reply')?.data,audio:events.some(e=>e.event==='audio'),error:events.find(e=>e.event==='error')?.data});console.log(JSON.stringify({guardRegression:id,state:done?.metrics?.state,actions:done?.metrics?.actions,proposed:done?.metrics?.modelProposedActions}));
}
await writeFile('research/final-integration-regression.json',JSON.stringify({at:new Date().toISOString(),note:'Post-benchmark explicit bound guard + default voice pipeline. Original 31-case scores are preserved; these additional checks do not silently replace model failures.',rows},null,2));
if(rows.some(r=>r.error||!r.audio)||rows[0].metrics?.state?.temperature?.passenger!==22||rows[1].metrics?.state?.temperature?.passenger!==25||rows[2].metrics?.state?.fan!==5||rows[3].metrics?.state?.defrost!==true)throw Error('Final integration regression failed');
