import WebSocket from 'ws';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base=process.env.TEST_BASE||'http://localhost:8787';
const results=[];
for(const language of ['en','ko']){
 const file=language==='en'?'public/sample-english.wav':'public/sample-command.wav';
 const wav=await readFile(file);let pcm;
 for(let offset=12;offset+8<=wav.length;){const size=wav.readUInt32LE(offset+4);if(wav.toString('ascii',offset,offset+4)==='data'){pcm=wav.subarray(offset+8,offset+8+size);break;}offset+=8+size+(size%2);}
 if(!pcm)throw Error('Missing WAV PCM');
 const session=await(await fetch(base+'/api/session',{method:'POST'})).json();
 const row={language,syntheticInput:true,reply:'',caption:'',captionIds:[],audioBytes:0};
 await new Promise(resolve=>{
  const ws=new WebSocket(base.replace(/^http/,'ws')+'/api/sonic?session='+session.id+'&language='+language,{origin:base});
  let interval,start,position=0,finished=false;
  const finish=()=>{if(finished)return;finished=true;clearTimeout(timeout);clearInterval(interval);ws.close();resolve();};
  const timeout=setTimeout(()=>{row.error='45 s timeout';finish();},45000);
  ws.on('error',error=>{row.error=error.message;finish();});
  ws.on('message',raw=>{
   const {event,data}=JSON.parse(raw);const ms=()=>Math.round(performance.now()-start);
   if(event==='ready'){
    start=performance.now();ws.send(JSON.stringify({type:'mode',mode:'file'}));
    interval=setInterval(()=>{if(ws.readyState!==1)return;if(position<pcm.length){ws.send(pcm.subarray(position,position+3200));position+=3200;if(position>=pcm.length)row.inputEndMs=ms();}else ws.send(Buffer.alloc(3200));},100);
   }
   if(event==='caption'){
    if(!row.captionIds.includes(data.id))row.captionIds.push(data.id);
    if(!data.final&&data.text)row.previewMs??=ms();
    if(data.final){row.finalCaptionMs=ms();row.caption=data.text;}
   }
   if(event==='text'&&data.role==='ASSISTANT'){row.finalTextMs??=ms();row.reply+=data.text;}
   if(event==='audio'){row.firstAudioMs??=ms();row.audioBytes+=Buffer.from(data.audio,'base64').length;}
   if(event==='tool'&&data.state)row.state=data.state;
   if(event==='error'){row.error=data.error;finish();}
   if(event==='done')finish();
  });
 });
 const exported=await(await fetch(base+'/api/export',{headers:{'X-Session-Id':session.id}})).json();
 row.exportMatchesFinal=exported.turns?.length===1&&exported.turns[0].reply===row.reply;
 row.previewLeadsAudioMs=row.firstAudioMs-row.previewMs;
 row.finalTextAfterFirstAudioMs=row.finalTextMs-row.firstAudioMs;
 row.pass=!row.error&&row.previewMs!=null&&row.previewMs<=row.firstAudioMs&&row.audioBytes>0&&row.caption===row.reply&&row.exportMatchesFinal&&row.captionIds.length===1&&(language==='en'?row.state?.temperature.driver===24:row.state?.temperature.passenger===25);
 results.push(row);console.log(JSON.stringify(row));
}
await mkdir('output',{recursive:true});await writeFile('output/sonic-caption-smoke.json',JSON.stringify({at:new Date().toISOString(),base,method:'Real-time synthetic audio input through deployed Sonic WebSocket; preview must precede first audio, final caption must equal canonical transcript, vehicle tool must execute.',results},null,2));
if(results.some(row=>!row.pass))process.exitCode=1;
