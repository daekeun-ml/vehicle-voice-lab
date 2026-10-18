import test from 'node:test';
import assert from 'node:assert/strict';
import {SonicSession} from '../sonic.mjs';
import {initialState} from '../vehicle.mjs';

test('Sonic records final spoken text and finishes a turn even without completionEnd',async()=>{
  const events=[];
  const s=new SonicSession({state:initialState(),emit:(type,data)=>events.push({type,data}),executeTool:()=>({ok:true})});
  await s.receive({contentStart:{contentId:'preview',role:'ASSISTANT',additionalModelFields:'{"generationStage":"SPECULATIVE"}'}});
  await s.receive({textOutput:{contentId:'preview',content:'Unspoken draft'}});
  await s.receive({contentStart:{contentId:'final',role:'ASSISTANT',additionalModelFields:'{"generationStage":"FINAL"}'}});
  await s.receive({textOutput:{contentId:'final',content:'Actual speech'}});
  await s.receive({contentEnd:{contentId:'final',completionId:'turn',stopReason:'END_TURN'}});
  await s.receive({completionEnd:{completionId:'turn'}});
  assert.deepEqual(events.filter(e=>e.type==='text').map(e=>e.data.text),['Actual speech']);
  assert.equal(events.filter(e=>e.type==='done').length,1);s.close();
});

test('Sonic cannot execute duplicate or canceled vehicle tool calls',async()=>{
  let calls=0;const s=new SonicSession({state:initialState(),emit:()=>{},executeTool:()=>{calls++;return{ok:true};}});
  const call={toolUseId:'one',toolName:'vehicle_control',content:'{"actions":[]}'};
  await s.tool(call);await s.tool(call);assert.equal(calls,1);
  s.close();await s.tool({...call,toolUseId:'two'});assert.equal(calls,1);
});

test('continuous Sonic microphone turns sharing completionId each finish exactly once',async()=>{
  const events=[];const s=new SonicSession({state:initialState(),emit:(type,data)=>events.push({type,data}),executeTool:()=>({ok:true})});
  for(let turn=1;turn<=3;turn++){
    await s.receive({contentStart:{contentId:`user-${turn}`,type:'TEXT',role:'USER',additionalModelFields:'{"generationStage":"FINAL"}'}});
    await s.receive({textOutput:{contentId:`user-${turn}`,content:'A new user request'}});
    await s.receive({contentEnd:{contentId:`user-${turn}`,completionId:'shared',stopReason:'END_TURN'}});
    await s.receive({contentStart:{contentId:`reply-${turn}`,type:'TEXT',role:'ASSISTANT',additionalModelFields:'{"generationStage":"FINAL"}'}});
    await s.receive({textOutput:{contentId:`reply-${turn}`,content:'Done'}});
    await s.receive({contentEnd:{contentId:`reply-${turn}`,completionId:'shared',stopReason:'END_TURN'}});
    await s.receive({completionEnd:{completionId:'shared'}});
  }
  assert.deepEqual(events.filter(e=>e.type==='done').map(e=>e.data.sonicTurn),[1,2,3]);s.close();
});
