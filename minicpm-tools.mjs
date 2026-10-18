// MiniCPM added a seat that was absent in the relative-temperature fixture.
// Ask for a target value rather than applying that unreliable interpretation.
export function guardMiniPlan(plan,state){
  const heard=typeof plan.heard==='string'?plan.heard:'';
  const relative=/(?:한|두|세|네|일|이|삼|사|[1-9])\s*도\s*(?:만\s*)?(?:올|내|높|낮)|온도(?:를|는|만)?\s*(?:조금|좀|더)?\s*(?:올|내|높|낮)|더워|추워/.test(heard);
  if(relative&&plan.actions.some(a=>a.type==='temperature')){
    // The earlier blanket guard also blocked correctly understood, explicit
    // seat requests. Permit only an exact match to the current state and heard
    // seat/delta; never repair or add a model action.
    const driver=/운전석/.test(heard),passenger=/조수석/.test(heard);
    const zone=driver&&!passenger?'driver':passenger&&!driver?'passenger':null;
    const amount=heard.match(/([1-9])\s*도/)?.[1]||(/(?:한|일)\s*도|온도(?:를|는|만)?\s*(?:조금|좀|더)?\s*(?:올|내|높|낮)|더워|추워/.test(heard)?'1':null);
    const direction=/올|높|추워/.test(heard)?1:/내|낮|더워/.test(heard)?-1:0;
    const expected=zone&&amount&&direction&&state?.temperature?.[zone]!=null?state.temperature[zone]+Number(amount)*direction:null;
    if(expected>=16&&expected<=30&&zone&&plan.actions.length===1&&plan.actions[0].type==='temperature'&&plan.actions[0].zone===zone&&plan.actions[0].value===expected)return{plan,reason:null};
    return{plan:{...plan,intent:'clarify',actions:[],reply:'어느 좌석 온도를 몇 도로 맞출까요? 예를 들어 “양쪽 온도를 23도로 맞춰줘”라고 말씀해 주세요.'},reason:'MiniCPM relative-temperature target is not reliable',proposedActions:plan.actions};
  }
  return{plan,reason:null};
}
