// Run on the Seoul web host with its instance role; no microphone/user data.
import{writeFile,mkdir}from'node:fs/promises';
import{executeAssistant,radioStations}from'../assistant-service.mjs';
const cases={weather:'서울 날씨 알려줘',places:'근처 카페 찾아줘',radio:'재즈 라디오 틀어줘',wiki:'경복궁 설명해줘',holidays:'다음 공휴일 언제야',exchange:'100달러 원화로 환율 계산해줘',sun:'강릉 일몰 알려줘',route:'서울시청에서 서울역까지 거리 알려줘',web:'한국 전기차 최근 뉴스',timer:'10분 타이머 맞춰줘',notes:'메모: 지하 2층 B12',calculate:'충전비 20kWh, kWh당 350원 계산해줘'};
const valid={weather:r=>Number.isFinite(r.temperature),places:r=>Array.isArray(r.items)&&r.items.length>0,radio:r=>r.items?.length>0,wiki:r=>r.title&&r.reply.length>30,holidays:r=>r.items?.length>0,exchange:r=>r.converted>0,sun:r=>r.sunset,route:r=>r.distanceMeters>0,web:r=>r.items?.length>0,timer:r=>r.effect?.timers?.length>0,notes:r=>r.notes?.length>0,calculate:r=>r.value===7000};
const report={at:new Date().toISOString(),host:'Seoul EC2 web backend',transport:'IAM-authenticated AgentCore Gateway, Tokyo; local utilities stay local',method:'3 consecutive serial calls per tool: first call plus two repeats. Provider caches included. p95 is nearest-rank (maximum with n=3). Includes MCP tool discovery on first call; excludes ASR, model inference, TTS and browser playback. Synthetic requests only. A smoke screen, not a load test.',cutoffMs:3000,tools:[],radioStreams:[]};
for(const[id,query]of Object.entries(cases)){
 const samples=[];
 for(let i=0;i<3;i++){
  const start=performance.now();try{const r=await executeAssistant({operation:id,query,language:'ko'},{},{diagnostic:true});samples.push({elapsedMs:Math.round(performance.now()-start),ok:r.ok===true&&!!valid[id](r),providerMs:r.elapsedMs,reply:r.reply?.slice(0,100),error:r.error,cachePosition:i===0?'first':'repeat'});}catch(e){samples.push({elapsedMs:Math.round(performance.now()-start),ok:false,error:e.message});}
 }
 const durations=samples.map(x=>x.elapsedMs).sort((a,b)=>a-b),successCount=samples.filter(x=>x.ok).length,medianMs=durations[1],p95Ms=durations[2];
 const row={id,sampleCount:3,successCount,medianMs,p95Ms,enabled:successCount===3&&p95Ms<=3000,samples};report.tools.push(row);console.log(JSON.stringify({id,successCount,medianMs,p95Ms,enabled:row.enabled}));
}
for(const station of radioStations){
 const start=performance.now(),controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);let bytes=0,firstByteMs=null;
 try{const r=await fetch(station.url,{signal:controller.signal});if(!r.ok)throw Error('HTTP '+r.status);if(!/audio\//.test(r.headers.get('content-type')||''))throw Error('Not audio');const reader=r.body.getReader();while(bytes<8192){const d=await reader.read();if(d.done)break;if(firstByteMs==null)firstByteMs=Math.round(performance.now()-start);bytes+=d.value.length;}await reader.cancel();report.radioStreams.push({id:station.id,ok:bytes>=8192,bytes,firstByteMs,contentType:r.headers.get('content-type')});}catch(e){report.radioStreams.push({id:station.id,ok:false,bytes,firstByteMs,error:e.message});}finally{clearTimeout(timer);controller.abort();}
 console.log(JSON.stringify(report.radioStreams.at(-1)));
}
const radio=report.tools.find(x=>x.id==='radio');if(!report.radioStreams.some(x=>x.ok&&x.firstByteMs<=3000))radio.enabled=false;
await mkdir('research',{recursive:true});await writeFile('research/assistant-tool-latency.json',JSON.stringify(report,null,2)+'\n');
