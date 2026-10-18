import {readFile,writeFile}from'node:fs/promises';
import {systemPrompt,initialState,parsePlan}from'../vehicle.mjs';
import {compactPlannerPrompt,compactKoreanPlannerPrompt}from'../planner-prompt-v2.mjs';
import {cases}from'./vehicle-benchmark-cases.mjs';
const m=JSON.parse(await readFile('model-catalog.json','utf8')).models.find(m=>m.id==='hyperclova-05b'),rows=[];
const selected=cases.filter(c=>['driver-24','passenger-25','fan-5','ac-off','defrost-off','seat-2','media-next','compound','out-of-range','clarify'].includes(c.id));
const canon=a=>a.flatMap(x=>x.type==='temperature'&&x.zone==='both'?[{...x,zone:'driver'},{...x,zone:'passenger'}]:[x]).map(x=>JSON.stringify(Object.fromEntries(Object.entries(x).sort()))).sort().join('|');
for(const[version,prompt]of Object.entries({'full-v1':systemPrompt,'compact-v2':compactPlannerPrompt,'korean-compact-v2':compactKoreanPlannerPrompt})){
 const row={version,tests:[]};for(const c of selected){let t={id:c.id};try{const r=await fetch('http://localhost:19101/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:m.repo,messages:[{role:'system',content:prompt+'\n현재 차량 상태: '+JSON.stringify(initialState())},{role:'user',content:c.text}]}),signal:AbortSignal.timeout(180000)});const d=await r.json();if(!r.ok)throw new Error(d.detail);const p=parsePlan(d.text);t={...t,passed:canon(p.actions)===canon(c.actions),actions:p.actions,reply:p.reply,llmMs:d.elapsedMs};}catch(e){t.passed=false;t.error=e.message;}row.tests.push(t);}row.passed=row.tests.filter(t=>t.passed).length;rows.push(row);console.log(JSON.stringify({version,passed:row.passed,total:row.tests.length}));await writeFile('research/korean-prompt-audit.json',JSON.stringify({model:m.id,at:new Date().toISOString(),method:'10 exact-transcript text cases; prompt language isolation. Not end-to-end audio score.',rows},null,2));
}
