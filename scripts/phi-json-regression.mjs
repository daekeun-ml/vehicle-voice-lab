import {readFile,writeFile} from 'node:fs/promises';
import {initialState,systemPrompt,parsePlan,executePlan} from '../vehicle.mjs';
const before=JSON.parse(await readFile('research/phi-json-before.json','utf8'));
const cases=before.map(row=>({name:'existing-history: '+row.input,request:row.request}));
for(const input of ['운전석 이십팔도로','운전석 온도를 28도로 맞춰줘','조수석 온도를 25도로 맞춰줘','앞유리 김서림 제거 켜줘','온도를 50도로 맞춰줘']){
 cases.push({name:'fresh: '+input,request:{model_id:'microsoft/Phi-4-mini-instruct',messages:[{role:'system',content:systemPrompt+'\n현재 차량 상태: '+JSON.stringify(initialState())},{role:'user',content:input}]}});
}
const results=[];
for(const c of cases){
 const response=await fetch('http://127.0.0.1:19101/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c.request),signal:AbortSignal.timeout(120000)});
 const d=await response.json(),row={name:c.name,status:response.status,...d};
 try{if(!response.ok)throw new Error(JSON.stringify(d));const plan=parsePlan(d.text);row.validJson=true;row.actions=plan.actions;const state=JSON.parse(c.request.messages[0].content.split('현재 차량 상태: ')[1]);row.state=executePlan(state,null,plan).state;}catch(e){row.error=e.message;}
 const input=c.request.messages.at(-1).content;
 row.expectedActions=input.includes('이십팔도로')||input.includes('28도로')?[{type:'temperature',zone:'driver',value:28}]:input.includes('25도로')?[{type:'temperature',zone:'passenger',value:25}]:input.includes('김서림')?[{type:'defrost',value:true}]:[];
 row.commandCorrect=JSON.stringify(row.actions)===JSON.stringify(row.expectedActions);
 results.push(row);console.log(JSON.stringify(row));
}
const report={at:new Date().toISOString(),purpose:'Phi JSON formatting regression; command accuracy evaluated separately',beforeInvalid:before.filter(r=>r.error).length,total:results.length,valid:results.filter(r=>r.validJson).length,commandCorrect:results.filter(r=>r.commandCorrect).length,results};
await writeFile('research/phi-json-regression.json',JSON.stringify(report,null,2));
if(report.valid!==report.total)process.exitCode=1;
