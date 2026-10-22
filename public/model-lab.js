const $=id=>document.getElementById(id);
const text=(ko,en)=>document.documentElement.lang==='en'?en:ko;
const create=(tag,value,parent)=>{const el=document.createElement(tag);if(value!=null)el.textContent=value;parent?.append(el);return el;};
const providers=new Map(),cards=new Map(),selected=new Set(['qwen17','supertonic']);
let running=false,controller,runId=0,summaryData,detailToken=0;
const examples={english:'The passenger temperature is now twenty four degrees.',temperature:'조수석 온도를 스물네 도로 맞췄어요.',negation:'에어컨을 끄지 않았어요.',decimal:'운전석은 22.5도, 조수석은 24도로 설정했어요.',rejection:'풍량 9단은 지원하지 않아요. 설정을 변경하지 않았어요.',destination:'목적지를 서울역에서 서울숲으로 바꿨어요.'};
function status(message){$('tts-test-status').textContent=message;}
function clearResult(card){card.audio.pause();card.audio.removeAttribute('src');card.audio.hidden=true;card.download.hidden=true;card.download.removeAttribute('href');if(card.url)URL.revokeObjectURL(card.url);card.url=null;card.result.textContent='';card.meta.textContent='';card.error.textContent='';}
function controls(){
 $('compare-tts').disabled=running||![...selected].some(id=>providers.get(id)?.ready!==false&&providers.has(id))||!$('tts-test-text').value.trim();
 $('cancel-tts-test').disabled=!running;$('tts-test-text').disabled=running;$('tts-test-example').disabled=running;
 $('tts-text-count').textContent=`${$('tts-test-text').value.length} / 350`;
 for(const [id,card]of cards){const p=providers.get(id);card.check.disabled=running||p.ready===false;card.generate.disabled=running||p.ready===false;card.apply.disabled=running||p.ready===false;
  card.generate.textContent=text('이 모델로 생성','Generate with this model');card.apply.textContent=text('차량 대화에 사용','Use for vehicle replies');card.selectLabel.textContent=text('비교 선택','Compare');card.download.textContent=text('음성 다운로드','Download audio');
  card.state.classList.toggle('unavailable',p.ready===false);card.state.textContent=p.ready===false?text('준비 중 · 지금은 실행 불가','Not ready · unavailable'):p.managed?text('AWS API · 생성 가능','AWS API · available'):text('연결됨 · 생성 가능','Ready · available');
 }
}
function addCard(p){
 const box=create('article',null,$('tts-model-grid'));box.className='tts-model-card'+(['qwen17','supertonic'].includes(p.id)?' new-provider':'');box.dataset.provider=p.id;
 if(p.notice)create('p',p.notice,box).className='tts-result-error';
 const title=create('div',null,box);title.className='tts-card-title';create('h3',p.name,title);
 const label=create('label',null,title);label.className='tts-select';const check=create('input',null,label);check.type='checkbox';check.checked=selected.has(p.id);check.setAttribute('aria-label',p.name+' '+text('비교 선택','compare'));
 const selectLabel=create('span',text('비교 선택','Compare'),label);check.addEventListener('change',()=>{check.checked?selected.add(p.id):selected.delete(p.id);controls();});
 const id=create('p',p.model,box);id.className='tts-model-id';id.dataset.noTranslate='';
 const state=create('span','',box);state.className='tts-model-state';const actions=create('div',null,box);actions.className='tts-card-actions';
 const generate=create('button',null,actions);generate.type='button';generate.addEventListener('click',()=>generateVoices([p.id]));
 const apply=create('button',null,actions);apply.type='button';apply.className='quiet';apply.addEventListener('click',()=>{
  for(const c of cards.values())c.audio.pause();document.dispatchEvent(new Event('vehicle-tts-lab-focus'));
  const engine=$('conversation-engine');if(!['cascade','minicpm-control','audio-control'].includes(engine.value)){engine.value='cascade';engine.dispatchEvent(new Event('change'));}
  const choice=$('tts-provider');choice.value=p.id;choice.dispatchEvent(new Event('change'));
  $('vehicle-workspace').scrollIntoView({behavior:'smooth',block:'start'});status(text('차량 대화의 응답 음성으로 선택했습니다.','Selected for vehicle replies.'));
 });
 const audio=create('audio',null,box);audio.controls=true;audio.preload='none';audio.hidden=true;audio.setAttribute('aria-label',p.name+' '+text('생성 음성','generated speech'));
 audio.addEventListener('play',()=>{document.dispatchEvent(new Event('vehicle-tts-lab-focus'));for(const c of cards.values())if(c.audio!==audio)c.audio.pause();});
 const download=create('a',text('음성 다운로드','Download audio'),box);download.hidden=true;download.className='tts-download';
 const result=create('p','',box);result.className='tts-result-text';result.dataset.noTranslate='';
 const meta=create('p','',box);meta.className='tts-result-meta';const error=create('p','',box);error.className='tts-result-error';error.setAttribute('role','status');
 cards.set(p.id,{box,check,selectLabel,state,generate,apply,audio,download,result,meta,error,url:null});
}
async function refreshProviders(){
 try{const r=await fetch('/api/tts');if(!r.ok)throw Error(r.status);const data=await r.json();
  const order=['qwen17','supertonic','ppaso','qwen','polly'];for(const p of data.providers.sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id))){providers.set(p.id,p);if(!cards.has(p.id))addCard(p);}
  if(!running)status(text('문장을 입력하고 생성할 모델을 선택하세요.','Enter text and choose a model.'));controls();
 }catch{if(!running)status(text('모델 연결 상태를 확인하지 못했습니다. 다시 시도해 주세요.','Could not load model status. Please retry.'));}
}
async function generateVoices(ids){
 if(running)return;const input=$('tts-test-text').value.trim();if(!input||input.length>350)return;
 ids=ids.filter(id=>providers.has(id)&&providers.get(id).ready!==false);if(!ids.length)return;
 running=true;controller=new AbortController();const mine=++runId;const signal=controller.signal;let session,completed=0;
 document.dispatchEvent(new Event('vehicle-tts-lab-focus'));for(const c of cards.values())c.audio.pause();for(const id of ids)clearResult(cards.get(id));controls();
 try{
  const r=await fetch('/api/session',{method:'POST',signal});if(!r.ok)throw Error(text('시험 세션을 만들지 못했습니다.','Could not create a test session.'));session=(await r.json()).id;
  for(const id of ids){
   signal.throwIfAborted();const card=cards.get(id);status(`${completed+1} / ${ids.length} · ${providers.get(id).name} · ${text('생성 중','generating')}`);
   const start=performance.now();
   try{
    const response=await fetch('/api/tts/preview',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':session},body:JSON.stringify({text:input,ttsProvider:id}),signal});
    const data=await response.json();if(!response.ok)throw Error(data.error||String(response.status));signal.throwIfAborted();if(mine!==runId)return;
    const bytes=Uint8Array.from(atob(data.audio),c=>c.charCodeAt(0));card.url=URL.createObjectURL(new Blob([bytes],{type:data.mediaType}));card.audio.src=card.url;card.audio.hidden=false;card.download.href=card.url;card.download.download=id+'-preview.wav';card.download.hidden=false;
    card.result.textContent=data.text;card.meta.textContent=`${text('도착까지','Ready in')} ${Math.round(performance.now()-start).toLocaleString()} ms · ${text('합성 처리','Synthesis')} ${data.inferenceMs.toLocaleString()} ms · ${data.voice}`;
    card.audio.dataset.model=data.model;card.audio.dataset.revision=data.revision||'';completed++;
   }catch(e){if(signal.aborted)throw e;card.error.textContent=e.message;}
  }
  status(text(`${completed}/${ids.length}개 생성 완료. 재생 버튼으로 비교하세요.`,`${completed}/${ids.length} generated. Use the audio controls to compare.`));
 }catch(e){status(signal.aborted?text('생성을 중단했습니다. 완료된 결과는 남겨 두었습니다.','Canceled. Completed results are retained.'):e.message);}
 finally{if(session)fetch('/api/session',{method:'DELETE',headers:{'X-Session-Id':session}}).catch(()=>{});if(mine===runId){running=false;controller=null;controls();}}
}
$('compare-tts').addEventListener('click',()=>generateVoices([...selected]));$('cancel-tts-test').addEventListener('click',()=>controller?.abort());
$('refresh-tts-lab').addEventListener('click',refreshProviders);$('tts-test-text').addEventListener('input',controls);
$('tts-test-example').addEventListener('change',e=>{$('tts-test-text').value=examples[e.target.value];controls();});

const date=value=>value?new Date(value).toLocaleString(document.documentElement.lang==='en'?'en-US':'ko-KR',{timeZone:'Asia/Seoul'})+' KST':'—';
function renderEvaluations(){
 const body=$('evaluation-rows');body.replaceChildren();const suite=$('evaluation-suite').value;
 const config=summaryData?.suites?.find(s=>s.id===suite),models=summaryData?.models||[];
 $('evaluation-score-label').textContent=suite==='original31'?text('앱 통과','App passed'):text('동작·상태 일치','Actions + state');
 if(!models.length){const row=create('tr',null,body);const c=create('td',text('이번 배포의 평가를 준비하고 있습니다.','Preparing this deployment’s evaluations.'),row);c.colSpan=6;$('evaluation-progress').textContent=text('평가 준비 중','Preparing');return;}
 const total=models.reduce((n,m)=>n+(m.suites[suite]?.total||0),0),done=models.reduce((n,m)=>n+(m.suites[suite]?.completed||0),0),finished=models.filter(m=>m.suites[suite]?.status==='complete').length;
 $('evaluation-progress').textContent=text(`${finished}/${models.length}개 설정 완료 · ${done}/${total}문제 실행`,`${finished}/${models.length} configurations complete · ${done}/${total} cases executed`);
 $('evaluation-method').textContent=document.documentElement.lang==='en'?(suite==='original31'?'App actions, state, reply rules and audio output · 25 base utterances + 3 alternate-voice + 3 noise variants':'Action/state checks and raw model actions are separate · 48 synthetic audio inputs with fixed context fixtures; reply semantics reviewed separately'):(config?.metric||'')+' · '+(config?.input||'');
 for(const model of models){const r=model.suites[suite]||{},row=create('tr',null,body);create('td',model.name,row);create('small',model.role==='sllm'?(r.asrId?`ASR: ${r.asrId} · ${r.promptVersion}`:text('STT → 텍스트 판단 모델','STT → text planner')):text('직접 음성 / 실시간 경로','Direct audio / realtime'),row.firstChild);
  create('td',`${r.completed||0} / ${r.total||config?.total||0}`,row);
  create('td',r.status==='blocked'&&!r.modelActionObserved?text('점수 없음','Not scored'):r.completed?`${suite==='original31'?r.passed:r.actionStateCorrect} / ${r.completed}`:'—',row);
  create('td',r.modelActionObserved?`${r.modelActionCorrect} / ${r.modelActionObserved}`:'—',row);
  create('td',r.medianFirstAudioMs==null?'—':`${(r.medianFirstAudioMs/1000).toFixed(2)} s`,row);
  const state=create('td',({complete:text('실행 완료','Executed'),running:text('실행 중','Running'),pending:text('대기','Pending'),deferred:text('보류 · 완료분 보존','Deferred · partial results saved'),blocked:text('실행 오류 확인 중','Investigating run error')})[r.status]||text('대기','Pending'),row);if(r.status==='complete')state.className='run-complete';
  if(r.errors)create('small',text(`실행 오류 ${r.errors}건`,`Execution errors: ${r.errors}`),state);
  if(r.timingExcluded)create('small',text(`유지보수 영향 ${r.timingExcluded}건 지연 집계 제외`,`Maintenance: ${r.timingExcluded} samples excluded from latency`),state);
  if(r.semanticReviewPending)create('small',text(`답변 의미 ${r.semanticReviewPending}건 검토 대기`,`${r.semanticReviewPending} replies awaiting semantic review`),state);
  if(r.strictPassed!=null)create('small',text(`답변 의미 포함 ${r.strictPassed}/${r.total} · AI 검토`,`Including reply meaning: ${r.strictPassed}/${r.total} · AI review`),state);
  const use=create('button',text('이 모델로 대화','Use this model'),state);use.className='quiet';use.type='button';use.addEventListener('click',()=>{for(const c of cards.values())c.audio.pause();document.dispatchEvent(new Event('vehicle-tts-lab-focus'));const engine=$('conversation-engine');engine.value=model.id==='sonic'?'sonic':model.role==='sllm'?'cascade':model.id==='minicpm-o45'?'minicpm-control':'audio-control';engine.dispatchEvent(new Event('change'));if(model.role==='sllm'){const picker=$('planner-model');picker.value=model.id;picker.dispatchEvent(new Event('change'));$('asr-model').value=r.asrId||picker.selectedOptions[0]?.dataset.asrId||'whisper';$('asr-model').dispatchEvent(new Event('change'));}else if(!['sonic','minicpm-o45'].includes(model.id)){$('audio-model').value=model.id;$('audio-model').dispatchEvent(new Event('change'));}document.querySelector('.conversation-settings').open=true;$('vehicle-workspace').scrollIntoView({behavior:'smooth',block:'start'});});
  if(r.completed){const button=create('button',text('입력·실패 상세','Inputs and failures'),state);button.className='quiet';button.type='button';button.addEventListener('click',()=>showDetails(suite,model));}
 }
 $('evaluation-updated').textContent=text('최근 갱신: ','Updated: ')+date(summaryData.updatedAt)+' · '+text(summaryData.timing||'','Shared Seoul GPU workers; initial model loads excluded from timing. Sonic uses end-of-input timing.')+(summaryData.runtimeAdjustments?.length?text(' · 메모리 관리 수정 및 환경 오류 재실행 기록 포함',' · Includes runtime memory fix and infrastructure retry records'):'');
}
async function refreshEvaluations(){try{const r=await fetch('/api/evaluations');if(!r.ok)throw Error(r.status);summaryData=await r.json();renderEvaluations();}catch{$('evaluation-progress').textContent=text('새 결과를 불러오지 못했습니다.','Unable to refresh results.');}}
async function showDetails(suite,model){
 const token=++detailToken,dialog=$('evaluation-detail'),body=$('evaluation-detail-body');$('evaluation-detail-title').textContent=model.name+' · '+(suite==='original31'?'31':'48');body.textContent=text('불러오는 중','Loading');dialog.showModal();
 try{const r=await fetch(`/api/evaluations/${suite}/${encodeURIComponent(model.id)}`);if(!r.ok)throw Error(text('기록을 불러오지 못했습니다.','Could not load this run.'));const run=await r.json();if(token!==detailToken)return;body.replaceChildren();
  create('p',text('고난도 점수는 동작·상태 자동 판정입니다. 답변 의미 검토는 별도로 표시합니다. 원문과 모델 출력을 그대로 제공합니다.','Hard-suite scores check actions/state automatically. Reply review is separate. Original inputs and outputs are shown unchanged.'),body);
  if(run.infrastructureAttempts?.length){const note=create('p',text(`초기 환경 오류 ${run.infrastructureAttempts.length}건은 기록을 보존하고 재실행했습니다. 본 점수와 구분합니다.`,`${run.infrastructureAttempts.length} initial infrastructure errors were retained and rerun separately.`),body);note.className='lab-method';}
  for(const row of run.rows){const detail=create('details',null,body);const headline=create('summary',`${row.id} · ${row.actionStateCorrect?'MATCH':'MISMATCH'} · ${row.text}`,detail);headline.dataset.noTranslate='';
   for(const [label,value]of [[text('인식/이해','Recognized/understood'),row.heard],[text('응답','Reply'),row.reply],[text('검증 메시지','Validation'),row.validationError||row.guardReason],[text('응답 판정 기준','Reply criteria'),row.replyRequirements?.join(' ')],[text('오류','Error'),row.error?.error]])if(value){const p=create('p',`${label}: ${value}`,detail);p.dataset.noTranslate='';}
   const data={expectedActions:row.expectedActions,modelProposedActions:row.modelProposedActions,actualActions:row.actualActions,expectedState:row.expectedState,actualState:row.actualState,modelActionCorrect:row.modelActionCorrect,actionStateCorrect:row.actionStateCorrect,semanticReview:row.semanticReview||null};
   const pre=create('pre',JSON.stringify(data,null,2),detail);pre.dataset.noTranslate='';
  }
 }catch(e){body.textContent=e.message;}
}
$('close-evaluation-detail').addEventListener('click',()=>{$('evaluation-detail').close();detailToken++;});
$('evaluation-detail').addEventListener('cancel',()=>{detailToken++;});$('evaluation-suite').addEventListener('change',renderEvaluations);$('refresh-evaluations').addEventListener('click',refreshEvaluations);
document.addEventListener('vehicle-ui-language',()=>{controls();renderEvaluations();});
window.addEventListener('pagehide',()=>{controller?.abort();for(const c of cards.values())if(c.url)URL.revokeObjectURL(c.url);});
controls();void refreshProviders();void refreshEvaluations();setInterval(()=>{if(!document.hidden){void refreshProviders();void refreshEvaluations();}},15000);
