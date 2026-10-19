// Synthetic Korean speech -> deployed Whisper -> tools -> Polly. No microphone data.
import{PollyClient,SynthesizeSpeechCommand}from'@aws-sdk/client-polly';
import{awsCredentials}from'../aws-auth.mjs';import{writeFile,mkdir}from'node:fs/promises';
const base=process.env.TEST_BASE;if(!base)throw Error('Set TEST_BASE to the deployed HTTPS demo');
const polly=new PollyClient({region:'ap-northeast-2',...awsCredentials});
const cases=[['weather','서울 날씨 알려줘'],['web','전기차 최근 뉴스 웹검색해줘'],['radio','재즈 라디오 틀어줘'],['wiki','경복궁 설명해줘'],['holidays','다음 공휴일 언제야'],['exchange','100달러 원화로 환율 계산해줘'],['sun','강릉 일몰 알려줘'],['route','서울시청에서 서울역까지 거리 알려줘'],['timer','10분 타이머 맞춰줘'],['notes','메모해줘 주차 위치 지하 2층 B12'],['calculate','충전비 20킬로와트시, 킬로와트시당 350원 계산해줘']];
const results=[];
function wav(pcm){const h=Buffer.alloc(44);h.write('RIFF');h.writeUInt32LE(pcm.length+36,4);h.write('WAVEfmt ',8);h.writeUInt32LE(16,16);h.writeUInt16LE(1,20);h.writeUInt16LE(1,22);h.writeUInt32LE(16000,24);h.writeUInt32LE(32000,28);h.writeUInt16LE(2,32);h.writeUInt16LE(16,34);h.write('data',36);h.writeUInt32LE(pcm.length,40);return Buffer.concat([h,pcm]);}
for(const[operation,text]of cases){
 const r=await polly.send(new SynthesizeSpeechCommand({Text:text,VoiceId:'Seoyeon',Engine:'neural',LanguageCode:'ko-KR',OutputFormat:'pcm',SampleRate:'16000'}));const audio=wav(Buffer.from(await r.AudioStream.transformToByteArray()));
 const s=await(await fetch(base+'/api/session',{method:'POST'})).json(),start=performance.now();
 const response=await fetch(base+'/api/turn',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':s.id},body:JSON.stringify({audio:audio.toString('base64'),asrId:'whisper',plannerId:'qwen35-4b-nf4',ttsProvider:'polly',inputMode:'file'})});
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',firstAudioMs=null,metrics,result,error,transcript;
 while(true){const d=await reader.read();if(d.done)break;buffer+=decoder.decode(d.value,{stream:true});let pos;
  while((pos=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,pos);buffer=buffer.slice(pos+2);const event=block.match(/^event: (.+)$/m)?.[1],raw=block.match(/^data: (.+)$/m)?.[1];if(!raw)continue;const data=JSON.parse(raw);if(event==='transcript')transcript=data.text;if(event==='assistant')result=data;if(event==='audio'&&firstAudioMs==null)firstAudioMs=Math.round(performance.now()-start);if(event==='done')metrics=data.metrics;if(event==='error')error=data.error;}
 }
 const pass=result?.operation===operation&&result?.ok===true&&firstAudioMs!=null&&!error&&metrics?.actions.length===0;
 const row={operation,syntheticText:text,transcript,pass,firstAudioMs,toolMs:result?.elapsedMs,reply:metrics?.reply,error,asrMs:metrics?.asrMs,ttsMs:metrics?.ttsMs};results.push(row);console.log(JSON.stringify(row));
}
await mkdir('output',{recursive:true});await writeFile('output/assistant-demo-smoke.json',JSON.stringify({at:new Date().toISOString(),method:'One Polly Seoyeon synthetic input per enabled tool, through CloudFront, Whisper and Polly output. First audio is first received audio event, not browser playback; input generation excluded.',results},null,2));
if(results.some(x=>!x.pass))process.exitCode=1;
