const $=id=>document.getElementById(id);
const names={whisper:'Whisper large-v3-turbo',nemotron:'Nemotron 3.5 ASR','qwen3-asr-06b':'Qwen3-ASR 0.6B','qwen3-asr-17b':'Qwen3-ASR 1.7B'};
let controller,sessionId,runId=0,evaluation;
const el=(tag,text,parent)=>{const node=document.createElement(tag);node.textContent=text;parent?.append(node);return node;};
async function wavBase64(file){
 if(!file||file.size>20_000_000)throw Error('20MB 이하 음성 파일을 선택해 주세요.');
 const ctx=new AudioContext();let audio;
 try{audio=await ctx.decodeAudioData(await file.arrayBuffer());}finally{await ctx.close();}
 if(audio.duration>30||audio.duration<=0)throw Error('30초 이하 음성이 필요합니다.');
 const offline=new OfflineAudioContext(1,Math.ceil(audio.duration*16000),16000),source=offline.createBufferSource();
 source.buffer=audio;source.connect(offline.destination);source.start();
 const samples=(await offline.startRendering()).getChannelData(0);
 const bytes=new Uint8Array(44+samples.length*2),view=new DataView(bytes.buffer);
 const str=(offset,text)=>[...text].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
 str(0,'RIFF');view.setUint32(4,bytes.length-8,true);str(8,'WAVEfmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,samples.length*2,true);
 samples.forEach((v,i)=>view.setInt16(44+i*2,Math.round(Math.max(-1,Math.min(1,v))*32767),true));
 let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
 return btoa(binary);
}
$('compare-asr').addEventListener('click',async()=>{
 const token=++runId;controller=new AbortController();const signal=controller.signal;
 $('compare-asr').disabled=true;$('cancel-asr').disabled=false;$('asr-file').disabled=true;$('asr-results').replaceChildren();
 document.dispatchEvent(new Event('vehicle-tts-lab-focus'));
 try{
  const audio=await wavBase64($('asr-file').files[0]);signal.throwIfAborted();
  const session=await(await fetch('/api/session',{method:'POST',signal})).json();sessionId=session.id;
  if(!sessionId)throw Error(session.error||'세션 생성 실패');
  for(const[id,name]of Object.entries(names)){
   signal.throwIfAborted();$('asr-test-status').textContent=name+' 인식 중 · 첫 모델 준비에는 시간이 걸립니다.';
   const card=el('article','',$('asr-results'));card.className='tts-model-card';card.dataset.asrId=id;el('h3',name,card);
   try{
    const r=await fetch('/api/asr/transcribe',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':sessionId},body:JSON.stringify({asrId:id,audio}),signal});
    const data=await r.json();if(!r.ok)throw Error(data.error);
    if(token!==runId)return;
    el('p',data.text||'(인식 결과 없음)',card).setAttribute('data-no-translate','');
    el('small',`인식 ${data.elapsedMs}ms · 요청 대기 ${data.queueMs||0}ms · 모델 로드 ${data.loadMs||0}ms · 요청 전체 ${data.requestMs}ms`,card);
    el('p',data.model,card).className='tts-model-id';card.dataset.model=data.model;card.dataset.revision=data.revision||'';
    const apply=el('button','차량 대화에 사용',card);apply.type='button';apply.className='quiet';
    apply.addEventListener('click',()=>{
     $('conversation-engine').value='cascade';$('conversation-engine').dispatchEvent(new Event('change'));
     $('asr-model').value=id;$('asr-model').dispatchEvent(new Event('change'));
     document.querySelector('.conversation-settings')?.setAttribute('open','');
     $('vehicle-workspace').scrollIntoView({behavior:'smooth'});
    });
   }catch(e){if(signal.aborted)throw e;el('p',e.message,card);}
  }
  $('asr-test-status').textContent='비교 완료 · 차량 설정은 변경하지 않았습니다.';
 }catch(e){$('asr-test-status').textContent=signal.aborted?'비교를 중단했습니다. 완료된 결과는 유지합니다.':e.message;}
 finally{
  if(sessionId)await fetch('/api/session',{method:'DELETE',headers:{'X-Session-Id':sessionId}}).catch(()=>{});
  sessionId=null;controller=null;$('compare-asr').disabled=false;$('cancel-asr').disabled=true;$('asr-file').disabled=false;
 }
});
$('cancel-asr').addEventListener('click',()=>controller?.abort());
function render(){
 if(!evaluation)return;
 $('asr-evaluation-status').textContent=`${evaluation.status==='complete'?'평가 완료':'평가 진행 중'} · ${(evaluation.models||[]).reduce((a,m)=>a+m.completed,0)} / ${(evaluation.models||[]).reduce((a,m)=>a+m.total,0)}건`;
 $('asr-evaluation-rows').replaceChildren();
 for(const model of evaluation.models||[]){
  const g=model.groups.find(g=>g.condition===$('asr-condition').value);if(!g)continue;
  const row=el('tr','',$('asr-evaluation-rows'));
  const ratio=k=>g.entities[k].total?`${g.entities[k].correct}/${g.entities[k].total}`:'—';
  for(const value of [names[model.id],`${g.completed}/${g.total}${g.errors?' · 오류 '+g.errors:''}`,g.cer==null?'—':(g.cer*100).toFixed(1)+'%',ratio('numbers'),ratio('seats'),ratio('destinations'),g.medianAsrMs==null?'—':g.medianAsrMs+'ms',`${g.actionStateCorrect}/${g.completed}`])el('td',value,row);
 }
}
async function refresh(){try{evaluation=await(await fetch('/api/asr/evaluation')).json();render();}catch{$('asr-evaluation-status').textContent='결과 조회 실패';}}
$('asr-condition').addEventListener('change',render);
refresh();setInterval(refresh,15000);
