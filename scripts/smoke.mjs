import {mkdir,writeFile} from 'node:fs/promises';
const base='http://localhost:8787';
const session=await(await fetch(base+'/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
const headers={'Content-Type':'application/json','X-Session-Id':session.id};
const results=[];
async function turn(payload){
  const started=performance.now();
  const response=await fetch(base+'/api/turn',{method:'POST',headers,body:JSON.stringify({ttsProvider:'qwen',...payload})});
  const text=await response.text();const events=text.split('\n\n').filter(Boolean).map(block=>{const lines=block.split('\n');return{event:lines[0].slice(7),data:JSON.parse(lines[1].slice(6))};});
  const error=events.find(e=>e.event==='error');if(error)throw new Error(error.data.error);
  const reply=events.find(e=>e.event==='reply')?.data,audio=events.find(e=>e.event==='audio')?.data,done=events.find(e=>e.event==='done')?.data;
  if(!reply||(payload.speak!==false&&!audio))throw new Error('Missing reply/audio');
  return {reply,done:done.metrics,elapsedMs:Math.round(performance.now()-started),audio:audio?.audio};
}
const scenarios=[
  ['운전석 온도를 24도로 맞춰줘',s=>s.temperature.driver===24&&s.temperature.passenger===22],
  ['아니 23도로 해줘',s=>s.temperature.driver===23&&s.temperature.passenger===22],
  ['음악 재생하고 음량은 20으로 해줘',s=>s.media.playing&&s.media.volume===20],
  ['앞유리 김서림 제거 켜줘',s=>s.defrost],
  ['온도를 50도로 맞춰줘',s=>s.temperature.driver===23&&s.temperature.passenger===22],
  ['집으로 안내해줘',s=>s.navigation.active&&s.navigation.destination?.includes('집')],
  ['방금 설정 되돌려',s=>!s.navigation.active&&s.navigation.destination===null],
];
await mkdir('output',{recursive:true});
for(const[input,check]of scenarios){
  try{
    const r=await turn({text:input,speak:results.length===0});const result={input,passed:!!check(r.reply.state),reply:r.reply.reply,state:r.reply.state,elapsedMs:r.elapsedMs,firstAudioReadyMs:r.done.serverAudioReadyMs,llmMs:r.done.llmMs,ttsMs:r.done.ttsMs};
    results.push(result);console.log(JSON.stringify(result));
  }catch(error){results.push({input,passed:false,error:error.message});console.log(JSON.stringify(results.at(-1)));}
  await writeFile('output/smoke-results.json',JSON.stringify({at:new Date().toISOString(),syntheticAudio:true,results},null,2));
}
const ttsResponse=await fetch('http://127.0.0.1:19102/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'조수석 온도를 이십오 도로 맞춰 주세요.'})});
if(!ttsResponse.ok)throw new Error('Synthetic input TTS failed');
const wav=Buffer.from(await ttsResponse.arrayBuffer());await writeFile('output/synthetic-command.wav',wav);
// Resample the generated WAV to the exact ASR format using macOS's available ffmpeg.
const {spawnSync}=await import('node:child_process');
const proc=spawnSync('ffmpeg',['-y','-i','output/synthetic-command.wav','-ar','16000','-ac','1','output/synthetic-command-16k.wav'],{encoding:'utf8'});
if(proc.status!==0)throw new Error(proc.stderr||'ffmpeg is required for integration smoke test');
const {readFile}=await import('node:fs/promises');
const voice=await turn({audio:(await readFile('output/synthetic-command-16k.wav')).toString('base64')});
const audioResult={input:'Synthetic Korean TTS → ASR → LLM → vehicle → TTS',transcript:voice.done.input,passed:voice.reply.state.temperature.passenger===25,reply:voice.reply.reply,asrMs:voice.done.asrMs,llmMs:voice.done.llmMs,ttsMs:voice.done.ttsMs,elapsedMs:voice.elapsedMs};
results.push(audioResult);console.log(JSON.stringify(audioResult));
await writeFile('output/smoke-results.json',JSON.stringify({at:new Date().toISOString(),syntheticAudio:true,results},null,2));
await writeFile('output/response.wav',Buffer.from(voice.audio,'base64'));
if(results.some(r=>!r.passed))process.exitCode=1;
