import {initialState,systemPrompt,parsePlan,executePlan} from '../vehicle.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
await mkdir('output',{recursive:true});
const catalog=JSON.parse(await readFile('model-catalog.json','utf8'));
const targets=process.argv.slice(2);const models=catalog.models.filter(m=>m.role==='sllm'&&(targets.length?targets.includes(m.id):['ready','integrating'].includes(m.status)));
const cases=[
  ['운전석 온도를 24도로 맞춰줘',s=>s.temperature.driver===24&&s.temperature.passenger===22],
  ['아니 23도로 해줘',s=>s.temperature.driver===23&&s.temperature.passenger===22],
  ['조수석 온도를 25도로 맞춰줘',s=>s.temperature.passenger===25&&s.temperature.driver===23],
  ['음악 재생하고 음량은 20으로 해줘',s=>s.media.playing&&s.media.volume===20],
  ['앞유리 김서림 제거 켜줘',s=>s.defrost],
  ['바람 세기를 3단으로 해줘',s=>s.fan===3],
  ['시트 열선을 2단으로 해줘',s=>s.seatHeat===2],
  ['집으로 안내해줘',s=>s.navigation.active&&s.navigation.destination?.includes('집')],
  ['방금 설정 되돌려',s=>!s.navigation.active&&s.navigation.destination===null],
  ['온도를 50도로 맞춰줘',s=>s.temperature.driver===23&&s.temperature.passenger===25],
];
const report={at:new Date().toISOString(),input:'Korean text, no ASR/TTS',timing:'GPU planner inference; model loading recorded separately',models:[]};
try{const previous=JSON.parse(await readFile('output/planner-evaluations.json','utf8'));report.models=previous.models.filter(row=>!models.some(model=>model.id===row.id));}catch{}
for(const model of models){
  let state=initialState(),previous,history=[];const rows=[];
  for(const [input,check]of cases){
    const row={input};
    try{
      const messages=[{role:'system',content:systemPrompt+'\n현재 차량 상태: '+JSON.stringify(state)},...history.slice(-12),{role:'user',content:input}];
      const response=await fetch('http://127.0.0.1:19101/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages,model_id:model.repo}),signal:AbortSignal.timeout(180000)});
      if(!response.ok)throw new Error(await response.text());const d=await response.json();Object.assign(row,{llmMs:d.elapsedMs,loadMs:d.loadMs,revision:d.revision});
      const plan=parsePlan(d.text),result=executePlan(state,previous,plan);state=result.state;previous=result.previous;history.push({role:'user',content:input},{role:'assistant',content:result.reply});
      Object.assign(row,{passed:!!check(state),reply:result.reply,actions:plan.actions,state:structuredClone(state)});
    }catch(error){Object.assign(row,{passed:false,error:error.message,state:structuredClone(state)});}
    rows.push(row);console.log(JSON.stringify({model:model.id,input,passed:row.passed,llmMs:row.llmMs,loadMs:row.loadMs,error:row.error}));
  }
  const values=rows.map(r=>r.llmMs).filter(Number.isFinite).sort((a,b)=>a-b),median=values.length?Math.round((values[Math.floor((values.length-1)/2)]+values[Math.floor(values.length/2)])/2):null;
  report.models.push({id:model.id,repo:model.repo,passed:rows.filter(r=>r.passed).length,total:rows.length,medianLlmMs:median,results:rows});
  await writeFile('output/planner-evaluations.json',JSON.stringify(report,null,2));
}
