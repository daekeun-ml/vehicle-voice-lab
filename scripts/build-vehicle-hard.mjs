// Offline only: validates authored reference answers, exports fixtures and a readable guide.
// Does not call a model, synthesize speech, change prompts, or update benchmark rankings.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir,writeFile} from 'node:fs/promises';
import {cases,suite,categories} from './vehicle-hard-cases.mjs';
import {cases as originalCases} from './vehicle-benchmark-cases.mjs';
import {initialState,executePlan,parsePlan} from '../vehicle.mjs';
import {guardExplicitBounds} from '../plan-guards.mjs';

const root=new URL('../',import.meta.url);
const destination=new URL('research/vehicle-hard-v1/',root);
const get=(object,path)=>path.split('.').reduce((node,key)=>node[key],object);
function set(object,path,value){
 const keys=path.split('.'),last=keys.pop();
 const parent=keys.reduce((node,key)=>{assert.ok(node&&Object.hasOwn(node,key),`Unknown patch path ${path}`);return node[key];},object);
 assert.ok(Object.hasOwn(parent,last),`Unknown patch field ${path}`);parent[last]=structuredClone(value);
}
const outcomeIntent={execute:'control',observe:'question','no-op':'question',clarify:'clarify',reject:'clarify'};
const rows=[];
assert.equal(cases.length,48);
assert.equal(new Set(cases.map(c=>c.id)).size,cases.length,'Duplicate IDs');
assert.equal(new Set(cases.map(c=>c.text)).size,cases.length,'Duplicate utterances');
assert.ok(cases.every(c=>!originalCases.some(old=>old.text===c.text)),'Original 25 commands must not be relabeled as hard');
for(const category of Object.keys(categories))assert.equal(cases.filter(c=>c.category===category).length,6,category);
for(const c of cases){
 assert.ok(categories[c.category],c.id);
 assert.ok(c.rationale?.length>10,c.id);
 assert.ok(c.text.length<=500,c.id);
 assert.ok(outcomeIntent[c.expected.outcome],c.id);
 assert.ok(c.expected.outcome==='execute'||c.expected.replyRequirements?.length,c.id);
 assert.equal(c.expected.outcome==='execute',c.expected.actions.length>0,c.id);
 let state=initialState(),previous=null;const history=[];
 for(const setup of c.setup){
  const before=structuredClone(state);
  const plan=parsePlan(JSON.stringify({intent:'control',actions:setup.actions,reply:''}));
  const result=executePlan(state,previous,plan);
  assert.deepEqual(state,before,'Fixture executor mutated input');
  state=result.state;previous=result.previous;
  history.push({role:'user',content:setup.text},{role:'assistant',content:result.reply});
 }
 assert.ok(history.length<=12,'Do not silently truncate the tested context');
 const input={state:structuredClone(state),previous:structuredClone(previous),history,utterance:c.text};
 const expectedState=structuredClone(state);
 for(const [path,value] of Object.entries(c.expected.patch))set(expectedState,path,value);
 expectedState.revision=state.revision+(c.expected.outcome==='execute'?1:0);
 for(const [path,value] of c.expected.facts||[])assert.deepEqual(get(state,path),value,`${c.id}: incorrect answer fact`);
 const referencePlan={intent:outcomeIntent[c.expected.outcome],actions:c.expected.actions,reply:''};
 parsePlan(JSON.stringify(referencePlan));
 const reference=executePlan(state,previous,referencePlan);
 // Compare independently authored state patches against the implementation; don't derive the answer from the actions alone.
 assert.deepEqual(reference.state,expectedState,`${c.id}: authored actions and independently authored state disagree`);
 assert.deepEqual(state,input.state,`${c.id}: mutated state`);
 assert.deepEqual(previous,input.previous,`${c.id}: mutated undo state`);
 if(c.expected.outcome==='execute')assert.deepEqual(reference.previous,input.state,`${c.id}: undo snapshot`);
 else assert.deepEqual(reference.previous,input.previous,`${c.id}: no-action changed undo snapshot`);
 for(const actions of c.allowedActionAlternatives||[]){
  const plan={intent:'control',actions,reply:''};parsePlan(JSON.stringify(plan));
  assert.deepEqual(executePlan(state,previous,plan).state,expectedState,`${c.id}: incorrect allowed alternative`);
 }
 // Diagnostic only: does today's lexical guard reject even the authored correct plan?
 const gate=guardExplicitBounds(c.text,referencePlan);
 rows.push({id:c.id,category:c.category,pair:c.pair||null,input,
  expected:{...c.expected,state:expectedState,allowedActionAlternatives:c.allowedActionAlternatives||[],orderedActions:c.orderedActions===true},
  rationale:c.rationale,
  currentGuardDiagnostic:{referencePlanBlocked:gate.reason!==null,reason:gate.reason,modelWasInvoked:false}});
}
for(const pair of new Set(rows.map(r=>r.pair).filter(Boolean)))assert.equal(rows.filter(r=>r.pair===pair).length,2,pair);
const counts=Object.fromEntries(Object.keys(categories).map(key=>[key,rows.filter(r=>r.category===key).length]));
const outcomes=Object.fromEntries(Object.keys(outcomeIntent).map(key=>[key,rows.filter(r=>r.expected.outcome===key).length]));
const artifact={suite,categories,counts,outcomes,cases:rows};
const json=JSON.stringify(artifact,null,2)+'\n';
await mkdir(destination,{recursive:true});
await writeFile(new URL('cases.json',destination),json);
const hash=createHash('sha256').update(json).digest('hex');
await writeFile(new URL('manifest.json',destination),JSON.stringify({suiteId:suite.id,version:suite.version,caseCount:rows.length,
 format:'UTF-8 JSON',sha256:hash,measured:false,audioGenerated:false,categories:counts,outcomes,
 validation:'48 authored reference plans, independent state patches, fixtures, alternatives, and answer facts checked offline',
 currentGuardBlocks:rows.filter(r=>r.currentGuardDiagnostic.referencePlanBlocked).map(r=>({id:r.id,...r.currentGuardDiagnostic})),
},null,2)+'\n');
let guide=`# 차량 음성 고난도 평가 v1 — 48문제\n\n[에셋 안내](README.md) · [기계 판독용 JSON](../research/vehicle-hard-v1/cases.json) · [문제 원본](../scripts/vehicle-hard-cases.mjs)\n\n`;
guide+='**기존 31개와 분리한 신규 언어 이해 챌린지입니다. 모델 평가와 음성 생성은 아직 하지 않았습니다.** 8개 유형 × 6문제이며, 단순 숫자 치환 대신 정정·부정 범위·다중 턴·상대 계산·비제어 발화를 시험합니다.\n\n';
guide+=`| 유형 | 문제 ID | 수 |\n| --- | --- | ---: |\n${Object.entries(categories).map(([key,title])=>`| ${title} | ${key}-01 ~ ${key}-06 | 6 |`).join('\n')}\n\n`;
guide+='## 이번 세트에서 어려운 점\n\n';
guide+='- 앞의 40도를 철회하고 24도로 정정하면 실행하고, 반대 순서라면 거부해야 합니다.\n- “마지막 발화”가 아니라 “마지막 온도 변경” 또는 “처음 변경한 좌석”을 찾아야 합니다.\n- 현재 상태가 같아도 두 번 곡 넘기기·일시 정지 후 재생을 생략하면 오답입니다.\n- 인용·가정·받아쓰기를 명령으로 실행하면 실패입니다. 반대로 명시적 실제 명령까지 거부해도 실패입니다.\n- 일부 요청은 정답이 확인 질문 또는 거부입니다. 무조건 actions=[]로 답하는 전략은 실행 문제에서 실패합니다.\n\n';
guide+=`| 기대 결과 | 문제 수 |\n| --- | ---: |\n${Object.entries(outcomes).map(([k,n])=>`| ${k} | ${n} |`).join('\n')}\n\n`;
guide+='## 판정 규칙을 먼저 고정하세요\n\n';
guide+='1. **모델 원안**: 가드 적용 전 intent·actions·응답 의미를 판정합니다. 서버가 잘못된 명령을 막아도 모델 정답으로 바꾸지 않습니다. 질문·거부의 intent는 의미가 같으면 question/clarify 차이만으로 탈락시키지 않습니다.\n';
guide+='2. **최종 앱 동작**: 전체 상태, 변경 번호 revision, 실행 동작 기록을 함께 검사합니다. 상태가 우연히 같다는 이유로 누락·중복 동작을 통과시키지 않습니다. 실행 결과에서 생성되는 성공 문구와 모델 자체 답변도 구분합니다.\n';
guide+='3. **비제어 응답**: 상태 유지뿐 아니라 아래의 질문·거부·사실 설명을 실제로 했는지 의미를 확인합니다. 정규식으로 “못/없/범위” 한 단어만 찾는 판정은 사용하지 않습니다.\n';
guide+='4. **동치 동작**: 서로 독립적인 설정 동작의 순서는 허용합니다. 온도의 both는 driver/passenger 두 동작으로 펼쳐 비교할 수 있습니다. 반복 미디어 동작은 횟수·순서를 보존합니다. 별도로 허용한 정답은 JSON의 allowedActionAlternatives에 있습니다. 그 외 임의 추가 동작은 허용하지 않습니다.\n';
guide+='5. **명시적인 평가 정책**: 일부만 지정한 좌석별 열선은 전체 열선으로 대체하지 않고 확인합니다. 도착 조건 예약은 지원하지 않습니다. undo는 단독, 동작은 한 요청 최대 6개입니다. 현재 프롬프트가 이 모든 고난도 상황을 해결한다고 가정하지 않습니다. 실패가 모델 한계인지 프롬프트·라우터·가드 한계인지 따로 기록합니다.\n\n';
guide+='이 문제들은 평가자에게 공개된 챌린지 세트입니다. 문제를 보고 프롬프트·가드를 수정했다면 이후 점수는 개발 세트 결과로 표기하세요. 별도의 미공개 최종 검증 세트가 필요합니다.\n\n';
guide+='## 입력과 정답을 섞지 마세요\n\n';
guide+='JSON의 `input`에는 현재 상태·직전 상태·검증된 대화 이력·평가 발화가 있습니다. 모델에는 실제 앱이 전달하는 현재 상태와 최근 대화, 평가 발화만 전달하고, `previous`는 실행기의 되돌리기 상태로 보관합니다. `expected`, `rationale`, `currentGuardDiagnostic`는 평가자 전용이며 모델 입력에 넣지 않습니다.\n\n';
guide+='선행 대화는 **고정된 정답 fixture**입니다. 선행 턴까지 같은 모델로 실행한 자유 대화 평가는 별도로 측정하세요. 현재 `/api/session`은 임의 상태·대화 이력 주입을 제공하지 않으므로 이 JSON을 기존 31개용 스크립트에 바로 넘겨 실행할 수는 없습니다. 향후 평가 어댑터는 이 fixture를 보존해야 합니다.\n\n';
guide+='음성 난도는 아직 측정하지 않았습니다. 먼저 정확한 텍스트 입력으로 판단 능력을 평가하고, 이후 동일 문장의 사람 녹음·자연스러운 정정·도로 소음으로 STT 포함 점수를 별도로 비교하세요. 인용부호에 의존하지 않도록 비제어 발화에는 “받아쓰기만”, “적용하지 마” 등 음성으로도 전달되는 조건을 넣었습니다.\n\n';
guide+='## 실제 모델 호출 없이 확인한 가드 충돌\n\n';
const blocked=rows.filter(r=>r.currentGuardDiagnostic.referencePlanBlocked);
if(blocked.length){
 guide+=blocked.map(r=>`- **${r.id}**: ${r.input.utterance} → 정답 계획도 현재 범위 가드에서 차단됩니다. 사유: ${r.currentGuardDiagnostic.reason}`).join('\n')+'\n\n';
 guide+='이는 모델 평가 결과가 아니라 **정답 계획을 현재 가드에 넣어 본 정적 호환성 진단**입니다. 기존 가드를 이 세트에 맞춰 수정하지 않았습니다.\n\n';
}
for(const [category,title] of Object.entries(categories)){
 guide+=`## ${title}\n\n`;
 for(const r of rows.filter(r=>r.category===category)){
  const authored=cases.find(c=>c.id===r.id);
  guide+=`### ${r.id}\n\n`;
  guide+=authored.setup.length?`선행 대화(모두 성공한 상태):\n\n${authored.setup.map((s,i)=>`${i+1}. ${s.text}`).join('\n')}\n\n`:'선행 대화 없음. 기본 상태: 양쪽 22도, 풍량 2, 에어컨 켜짐, 김서림 제거 꺼짐, 열선 0, 음악 정지, 음량 35, 목적지 없음.\n\n';
  guide+=`**평가 발화:** ${r.input.utterance}\n\n**기대 결과:** ${r.expected.outcome}\n\n`;
  if(r.expected.actions.length){
   guide+='```json\n'+JSON.stringify(r.expected.actions,null,2)+'\n```\n\n';
   guide+=Object.keys(r.expected.patch).length?`상태 변경: ${Object.entries(r.expected.patch).map(([k,v])=>'`'+k+' = '+JSON.stringify(v)+'`').join(', ')}. 나머지 값은 보존.\n\n`:'최종 상태 값은 이전과 같지만 지정한 동작을 반드시 실행하고 revision은 1 증가해야 합니다.\n\n';
   if(r.expected.allowedActionAlternatives.length)guide+=`허용하는 동치 동작: \`${JSON.stringify(r.expected.allowedActionAlternatives)}\`.\n\n`;
   if(r.expected.orderedActions)guide+='**동작 순서·횟수까지 일치해야 합니다.**\n\n';
  }else{
   guide+='`actions=[]`. 상태·revision·되돌리기 스냅샷을 변경하지 않습니다.\n\n';
   guide+=r.expected.replyRequirements.map(x=>'- '+x).join('\n')+'\n\n';
  }
  guide+=`**어려운 이유:** ${r.rationale}\n\n`;
 }
}
guide+='## 재생성과 검증\n\n```bash\nnode scripts/build-vehicle-hard.mjs\n```\n\n이 명령은 AWS·모델 API를 호출하지 않습니다. 문제 수·중복·선행 상태·정답 동작과 독립적으로 작성한 상태 변경값·대안 동작·질문의 현재 상태 사실을 검증하고 JSON과 이 문서를 다시 만듭니다. 자연어 정답의 의미 검토는 별도로 필요합니다.\n\n';
guide+=`정답 JSON SHA-256: \`${hash}\`. [manifest](../research/vehicle-hard-v1/manifest.json)에 음성 미생성·모델 미평가 상태와 함께 기록했습니다.\n`;
await writeFile(new URL('asset-guide/HARD_BENCHMARK.md',root),guide);
console.log(JSON.stringify({suite:suite.id,cases:rows.length,outcomes,referenceValidation:'passed',currentGuardBlocks:blocked.map(r=>r.id),modelInvoked:false,audioGenerated:false,sha256:hash},null,2));
