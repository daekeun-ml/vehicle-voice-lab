// Validate explicit user bounds without creating or repairing any model action.
export function guardExplicitBounds(text,plan){
 const rules=[
  {type:'temperature',pattern:/(?:온도|운전석|조수석|양쪽)[^\d]{0,20}(\d+(?:\.\d+)?)\s*도/,min:16,max:30,message:'온도는 16~30도 사이로 말씀해 주세요.'},
  {type:'fan',pattern:/(?:바람\s*세기|풍량|바람)[^\d]{0,15}(\d+)\s*단/,min:1,max:7,message:'바람 세기는 1~7단 사이로 말씀해 주세요.'},
  {type:'seatHeat',pattern:/(?:시트\s*열선|열선)[^\d]{0,15}(\d+)\s*단/,min:0,max:3,message:'열선은 0~3단 사이로 말씀해 주세요.'},
 ];
 for(const rule of rules){
  const input=String(text||''),match=input.match(rule.pattern),value=match?.[1];
  if(value===undefined)continue;
  // "1도 올려" is a delta, while "1도로 맞춰" is an absolute target.
  const relative=rule.type==='temperature'&&/^\s*(?:(?:만|씩|정도|가량|를|더|좀)\s*){0,3}(?:올[려리]|내[려리]|높[여이]|낮[춰추])/.test(input.slice(match.index+match[0].length));
  const outside=relative?Number(value)>rule.max-rule.min:Number(value)<rule.min||Number(value)>rule.max;
  if(outside&&plan.actions.some(a=>a.type===rule.type))return{plan:{...plan,intent:'clarify',actions:[],reply:'설정을 적용하지 않았어요. '+rule.message},reason:rule.message,proposedActions:plan.actions};
 }
 return{plan,reason:null};
}
