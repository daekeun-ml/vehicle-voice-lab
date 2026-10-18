import test from 'node:test';
import assert from 'node:assert/strict';
import {guardMiniPlan} from '../minicpm-tools.mjs';
import {initialState,executePlan} from '../vehicle.mjs';

test('MiniCPM cannot apply a fabricated seat for an untrusted relative temperature request',()=>{
  for(const heard of ['운전석 온도 1도 올려줘','온도를 한 도 올려줘','온도 좀 내려줘','추워']){
    const proposal={heard,intent:'control',actions:[{type:'temperature',zone:'driver',value:23}],reply:''};
    const guarded=guardMiniPlan(proposal),state=initialState();
    assert.equal(guarded.plan.intent,'clarify');assert.deepEqual(executePlan(state,null,guarded.plan).state,state);assert.deepEqual(proposal.actions,guarded.proposedActions);
  }
});
test('explicit temperature targets and defrost commands keep their validated actions',()=>{
  for(const plan of [
    {heard:'운전석 온도를 24도로 올려줘',intent:'control',actions:[{type:'temperature',zone:'driver',value:24}],reply:''},
    {heard:'김서림 제거 켜줘',intent:'control',actions:[{type:'defrost',value:true}],reply:''}
  ])assert.equal(guardMiniPlan(plan).plan,plan);
});

test('a correct explicit-seat relative request passes; wrong seat or delta remains blocked',()=>{
 const state={temperature:{driver:22,passenger:25}},plan={intent:'control',heard:'운전석 온도를 1도 올려줘',actions:[{type:'temperature',zone:'driver',value:23}],reply:''};
 assert.deepEqual(guardMiniPlan(plan,state).plan.actions,plan.actions);
 assert.equal(guardMiniPlan({...plan,actions:[{type:'temperature',zone:'passenger',value:26}]},state).plan.actions.length,0);
 assert.equal(guardMiniPlan({...plan,actions:[{type:'temperature',zone:'driver',value:24}]},state).plan.actions.length,0);
});
