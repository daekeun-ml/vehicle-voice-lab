import {readFile,writeFile,access} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const rows=[];
for(const id of ['step-audio2-mini','mimo-audio','qwen3-omni']){
 const input=`output/speech-alternatives/${id}-ko.wav`,normalized=`output/speech-alternatives/${id}-ko-16k.wav`;
 try{await access(input);}catch{continue;}
 execFileSync('ffmpeg',['-y','-i',input,'-ar','16000','-ac','1',normalized],{stdio:'ignore'});
 const form=new FormData();form.append('file',new Blob([await readFile(normalized)],{type:'audio/wav'}),'native-output.wav');
 const r=await fetch('http://127.0.0.1:19101/asr',{method:'POST',body:form});const d=await r.json();rows.push({id,asrText:d.text,asrMs:d.elapsedMs,status:r.status});console.log(JSON.stringify(rows.at(-1)));
}
await writeFile('research/native-korean-asr.json',JSON.stringify({at:new Date().toISOString(),method:'ko-KR Nemotron ASR of native generated Korean-mode audio; diagnostic only, not a human listening evaluation',rows},null,2));
