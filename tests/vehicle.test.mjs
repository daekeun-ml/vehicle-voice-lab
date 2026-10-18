import test from 'node:test';
import assert from 'node:assert/strict';
import {initialState,parsePlan,executePlan} from '../vehicle.mjs';

const plan=actions=>({intent:'control',actions,reply:''});
test('compound controls commit atomically and undo restores all changes',()=>{
  const original=initialState();
  const result=executePlan(original,null,plan([{type:'temperature',zone:'driver',value:24},{type:'media',value:'play'},{type:'volume',value:20}]));
  assert.equal(result.state.temperature.driver,24);assert.equal(result.state.temperature.passenger,22);assert.equal(result.state.media.playing,true);assert.equal(result.state.media.volume,20);
  const restored=executePlan(result.state,result.previous,plan([{type:'undo'}]));
  assert.deepEqual({...restored.state,revision:0},original);assert.equal(restored.state.revision,2);
});
test('invalid second action cannot partially mutate the vehicle',()=>{
  const original=initialState();
  assert.throws(()=>executePlan(original,null,plan([{type:'temperature',zone:'both',value:24},{type:'volume',value:150}])));
  assert.deepEqual(original,initialState());
});
test('unsupported driving controls and invalid types are rejected',()=>{
  for(const action of [{type:'accelerate',value:90},{type:'temperature',zone:'both',value:'24'},{type:'temperature',zone:'rear',value:24},{type:'ac',value:'false'},{type:'fan',value:2.5}])assert.throws(()=>executePlan(initialState(),null,plan([action])));
});
test('question plans cannot smuggle vehicle actions',()=>{
  assert.throws(()=>parsePlan('{"intent":"question","actions":[{"type":"ac","value":false}],"reply":"현재 상태"}'));
  assert.equal(executePlan(initialState(),null,{intent:'question',actions:[],reply:'현재 22도예요.'}).state.revision,0);
});
test('Phi whitespace truncation is rejected before any vehicle action runs',()=>{
  const state=initialState();
  const truncated='{\r\n  "intent": "control",\n  "reply": "운전석 온도를 28도로 맞췄어요."\n '+ '\r'.repeat(360);
  assert.throws(()=>executePlan(state,null,parsePlan(truncated)),/차량 명령을 완성하지 못했어요/);
  assert.deepEqual(state,initialState());
});
test('truncated plans with already generated actions cannot change the vehicle',()=>{
  const state=initialState();
  assert.throws(()=>executePlan(state,null,parsePlan('{"intent":"control","actions":[{"type":"temperature","zone":"driver","value":28}],"reply":"')));
  assert.deepEqual(state,initialState());
});
