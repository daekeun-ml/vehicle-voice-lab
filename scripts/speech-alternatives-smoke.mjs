import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {systemPrompt,initialState,parsePlan,executePlan} from '../vehicle.mjs';
const nativeOnly=process.argv.includes('--native-only');const targets=process.argv.slice(2).filter(a=>a!=='--native-only');const ids=targets.length?targets:['qwen3-omni','step-audio2-mini','mimo-audio','moshi'];
await mkdir('output/speech-alternatives',{recursive:true});
let previousRows=[];let report={at:new Date().toISOString(),method:'Synthetic WAV input; native audio presence and schema/tool tests, not human speech quality',models:[]};
try{const previous=JSON.parse(await readFile('research/speech-alternatives-evaluation.json','utf8'));previousRows=previous.models;report.models=previous.models.filter(r=>!ids.includes(r.id));}catch{}
for(const id of ids){
 const row={id,tests:nativeOnly?(previousRows.find(r=>r.id===id)?.tests||[]).filter(t=>t.operation!=='s2s'):[]};
 for(const language of ['en','ko']){
  if(row.loadFailed)break;
  const wav=await readFile(language==='ko'?'public/sample-command.wav':'public/sample-english.wav');
  const expected=language==='ko'?[{type:'temperature',zone:'passenger',value:25}]:[{type:'temperature',zone:'driver',value:24}];
  for(const operation of nativeOnly||id==='moshi'?['s2s']:['plan-audio','s2s']){
   if(row.loadFailed)break;
   const form=new FormData();form.append('file',new Blob([wav],{type:'audio/wav'}),'sample.wav');form.append('model_id',id);form.append('language',language);form.append('messages',JSON.stringify([{role:'system',content:systemPrompt+'\n현재 차량 상태: '+JSON.stringify(initialState())+'\nAlso include a heard string describing the audio request. Return JSON only.'}]));
   const test={language,operation};
   try{
    const r=await fetch('http://127.0.0.1:19104/'+operation,{method:'POST',body:form,signal:AbortSignal.timeout(600000)});const data=await r.json();Object.assign(test,{status:r.status,model:data.model,revision:data.revision,quantization:data.quantization,elapsedMs:data.elapsedMs,loadMs:data.loadMs});
    if(!r.ok)throw new Error(data.detail||JSON.stringify(data));
    if(operation==='plan-audio'){
     const p=parsePlan(data.text);test.jsonValid=true;test.actions=p.actions;test.heard=p.heard;test.reply=p.reply;test.expectedActions=expected;test.commandCorrect=JSON.stringify(p.actions)===JSON.stringify(expected);test.state=executePlan(initialState(),null,p).state;
    }else{
     const bytes=Buffer.from(data.audio,'base64');test.audioBytes=bytes.length;test.nativeAudio=bytes.length>1000&&(bytes.subarray(0,4).toString()==='RIFF'||bytes.subarray(0,4).toString()==='RF64');test.reply=data.text;
     if(!test.nativeAudio)throw new Error('Missing native WAV audio');
     const path=`output/speech-alternatives/${id}-${language}.wav`;await writeFile(path,bytes);
     const stats=spawnSync('ffmpeg',['-hide_banner','-i',path,'-af','volumedetect','-f','null','-'],{encoding:'utf8'});const level=stats.stderr?.match(/mean_volume: ([-\w.]+) dB/)?.[1];test.meanDb=level;test.nonSilent=!!(level&&Number(level)>-65);if(!test.nonSilent){test.nativeAudio=false;throw new Error('Native WAV was silent or could not be decoded');}
    }
   }catch(error){test.error=error.message;if(test.status===503)row.loadFailed=true;}
   row.tests.push(test);console.log(JSON.stringify({id,...test}));
   await writeFile('research/speech-alternatives-evaluation.partial.json',JSON.stringify(row,null,2));
  }
 }
 row.nativeVerified=row.tests.some(t=>t.nativeAudio&&!t.error);row.audioPlannerVerified=row.tests.some(t=>t.jsonValid&&!t.error);row.koreanCommandPassed=row.tests.some(t=>t.language==='ko'&&t.commandCorrect&&!t.error);report.models.push(row);
 await writeFile('research/speech-alternatives-evaluation.json',JSON.stringify(report,null,2));
}
