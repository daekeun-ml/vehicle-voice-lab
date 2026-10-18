// Regression: several spoken turns on ONE continuous Bedrock audio connection.
import WebSocket from 'ws';
import {readFile,writeFile} from 'node:fs/promises';
const base='http://localhost:8787';
const s=await(await fetch(base+'/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
const ws=new WebSocket(`ws://localhost:8787/api/sonic?session=${s.id}&language=ko`,{origin:base});
let pending,pcm,position=0,ticker,readyResolve,readyReject,latestState=s.state;
const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject;});
const connectTimer=setTimeout(()=>readyReject(new Error('Connection timeout')),15000);
ws.on('error',error=>{readyReject(error);pending?.reject(error);});
ws.on('message',raw=>{
  const {event,data}=JSON.parse(raw);
  if(event==='ready'){clearTimeout(connectTimer);readyResolve();}
  if(event==='error'){readyReject(new Error(data.error));pending?.reject(new Error(data.error));}
  if(!pending)return;
  if(event==='text')pending.result[data.role==='USER'?'transcript':'reply']+=data.text;
  if(event==='audio')pending.result.audioBytes+=Buffer.from(data.audio,'base64').length;
  if(event==='tool'&&data.state){latestState=data.state;pending.result.state=data.state;}
  if(event==='done'){pending.result.completionId=data.completionId;pending.result.sonicTurn=data.sonicTurn;pending.resolve();}
});
function dataChunk(wav){let i=12;while(i+8<=wav.length){const n=wav.readUInt32LE(i+4);if(wav.toString('ascii',i,i+4)==='data')return wav.subarray(i+8,i+8+n);i+=8+n+(n%2);}throw new Error('Invalid WAV');}
const results=[];
try{
  await ready;
  ticker=setInterval(()=>{if(ws.readyState!==1)return;if(pcm&&position<pcm.length){ws.send(pcm.subarray(position,position+3200));position+=3200;}else ws.send(Buffer.alloc(3200));},100);
  for(const [file,zone,value]of[['public/sample-command.wav','passenger',25],['public/sample-english.wav','driver',24],['public/sample-command.wav','passenger',25]]){
    const result={file,transcript:'',reply:'',audioBytes:0};
    let timeout;
    const done=new Promise((resolve,reject)=>{pending={result,resolve,reject};timeout=setTimeout(()=>reject(new Error('Turn completion timeout')),25000);});
    ws.send(JSON.stringify({type:'mode',mode:'file'}));pcm=dataChunk(await readFile(file));position=0;
    try{await done;}finally{clearTimeout(timeout);}
    // Repeating an already-applied setting can legitimately return speech without another tool call.
    result.state??=structuredClone(latestState);
    result.passed=result.audioBytes>0&&result.state?.temperature[zone]===value;
    if(!result.passed)throw new Error('Missing speech or incorrect vehicle state');
    results.push(result);console.log(JSON.stringify({turn:results.length,passed:result.passed,sonicTurn:result.sonicTurn,completionId:result.completionId}));pending=null;
  }
  const exported=await(await fetch(base+'/api/export',{headers:{'X-Session-Id':s.id}})).json();
  if(exported.turns.length!==3||!exported.turns.every(t=>t.completed))throw new Error('Incomplete conversation records');
  await writeFile('output/sonic-multiturn.json',JSON.stringify({at:new Date().toISOString(),singleConnection:true,results},null,2));
}finally{clearTimeout(connectTimer);clearInterval(ticker);ws.close();}
