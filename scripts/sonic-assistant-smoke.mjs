import WebSocket from'ws';import{writeFile,mkdir}from'node:fs/promises';
const base=process.env.TEST_BASE;if(!base)throw Error('Set TEST_BASE');
const cases=[['exchange','Convert 100 US dollars to Korean won.'],['radio','Play jazz radio.'],['timer','Set a timer for ten minutes.']];const results=[];
for(const[operation,text]of cases){
 const session=await(await fetch(base+'/api/session',{method:'POST'})).json();
 const result={operation,text,tools:[],reply:'',audioBytes:0};
 await new Promise(resolve=>{
  const ws=new WebSocket(base.replace(/^http/,'ws')+'/api/sonic?session='+session.id+'&language=en',{origin:base}),start=performance.now();
  let silence;const finish=()=>{clearTimeout(timer);clearInterval(silence);ws.close();resolve();};
  const timer=setTimeout(()=>{result.error='45 s timeout';finish();},45000);
  ws.on('message',message=>{const{event,data}=JSON.parse(message);if(event==='ready'){ws.send(JSON.stringify({type:'text',text}));silence=setInterval(()=>{if(ws.readyState===1)ws.send(Buffer.alloc(3200));},100);}if(event==='tool')result.tools.push({operation:data.operation,ok:data.ok,elapsedMs:data.elapsedMs,effect:data.effect,amount:data.amount,converted:data.converted});if(event==='text'&&data.role==='ASSISTANT')result.reply+=data.text;if(event==='audio'){result.firstAudioMs??=Math.round(performance.now()-start);result.audioBytes+=Buffer.from(data.audio,'base64').length;}if(event==='error'){result.error=data.error;finish();}if(event==='done')finish();});ws.on('error',e=>{result.error=e.message;finish();});
 });
 result.pass=result.tools.some(x=>x.operation===operation&&x.ok&&(operation!=='timer'||x.effect?.timers?.length>0)&&(operation!=='exchange'||x.amount===100))&&result.audioBytes>0&&!result.error;results.push(result);console.log(JSON.stringify(result));
}
await mkdir('output',{recursive:true});await writeFile('output/sonic-assistant-smoke.json',JSON.stringify({at:new Date().toISOString(),method:'English text inputs through the deployed Sonic bidirectional connection; real tool calls and native audio required. First audio may precede completion of a tool (spoken acknowledgement).',results},null,2));if(results.some(x=>!x.pass))process.exitCode=1;
