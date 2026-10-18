import WebSocket from 'ws';
import {readFile,writeFile} from 'node:fs/promises';
const base=process.env.TEST_BASE||'http://localhost:8787';
const origin=process.env.TEST_ORIGIN||base,headers=process.env.ORIGIN_VERIFY_SECRET?{'X-Vehicle-Origin-Key':process.env.ORIGIN_VERIFY_SECRET}:{};
async function probe(language,file,expected){
  const s=await(await fetch(base+'/api/session',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:'{}'})).json();
  const wav=await readFile(file);let offset=12,pcm;
  while(offset+8<=wav.length){const size=wav.readUInt32LE(offset+4);if(wav.toString('ascii',offset,offset+4)==='data'){pcm=wav.subarray(offset+8,offset+8+size);break;}offset+=8+size+(size%2);}
  if(!pcm)throw new Error('Missing WAV data');
  const result={language,syntheticInput:true,model:'amazon.nova-2-5-sonic',region:'ap-northeast-1',transcript:'',reply:'',audioBytes:0};
  let timer,silence,position=0,inputEnd,firstAudio;
  await new Promise((resolve,reject)=>{
    const ws=new WebSocket(`${base.replace(/^http/,'ws')}/api/sonic?session=${s.id}&language=${language}`,{origin,headers});
    const finish=error=>{clearTimeout(timer);clearInterval(silence);ws.close();error?reject(error):resolve();};
    timer=setTimeout(()=>finish(new Error('Sonic probe timeout')),45000);
    ws.on('error',finish);
    ws.on('message',raw=>{
      const {event,data}=JSON.parse(raw);
      if(event==='ready'){
        ws.send(JSON.stringify({type:'mode',mode:'file'}));
        silence=setInterval(()=>{if(ws.readyState!==1)return;if(position<pcm.length){ws.send(pcm.subarray(position,position+3200));position+=3200;if(position>=pcm.length)inputEnd=performance.now();}else ws.send(Buffer.alloc(3200));},100);
      }
      if(event==='text')result[data.role==='USER'?'transcript':'reply']+=data.text;
      if(event==='audio'){result.audioBytes+=Buffer.from(data.audio,'base64').length;firstAudio??=performance.now();}
      if(event==='tool')result.state=data.state;
      if(event==='error')finish(new Error(data.error));
      if(event==='done'&&result.audioBytes)finish();
    });
  });
  result.firstAudioAfterInputEndMs=Math.round(firstAudio-inputEnd);result.commandCorrect=expected(result.state);result.audioGenerated=result.audioBytes>0;
  return result;
}
const results=[];
for(const [language,file,expected]of[
  ['en','public/sample-english.wav',s=>s?.temperature.driver===24],
  ['ko','public/sample-command.wav',s=>s?.temperature.passenger===25],
]){
  try{results.push(await probe(language,file,expected));}catch(error){results.push({language,error:error.message});}
  console.log(JSON.stringify(results.at(-1)));
}
await writeFile(process.env.TEST_BASE?'output/sonic-cloud-smoke.json':'output/sonic-smoke.json',JSON.stringify({at:new Date().toISOString(),base,results},null,2));
if(!results[0].commandCorrect||!results[0].audioGenerated)process.exitCode=1;
