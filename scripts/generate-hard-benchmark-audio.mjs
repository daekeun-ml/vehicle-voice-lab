import {PollyClient,SynthesizeSpeechCommand} from '@aws-sdk/client-polly';
import {awsCredentials} from '../aws-auth.mjs';
import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const fixtures=JSON.parse(await readFile('research/vehicle-hard-v1/cases.json','utf8'));
const dir='output/vehicle-hard-v1';await mkdir(dir,{recursive:true});
const polly=new PollyClient({region:process.env.AWS_REGION||'ap-northeast-2',...awsCredentials});
const manifest={suiteId:'vehicle-hard-v1',generatedAt:new Date().toISOString(),synthetic:true,voice:'Polly neural Seoyeon',realCarNoise:false,items:[]};
for(const c of fixtures.cases){
 const file=`${dir}/${c.id}.wav`;
 try{await access(file);}catch{
  const r=await polly.send(new SynthesizeSpeechCommand({Engine:'neural',VoiceId:'Seoyeon',LanguageCode:'ko-KR',OutputFormat:'pcm',SampleRate:'16000',Text:c.input.utterance}));
  const pcm=Buffer.from(await r.AudioStream.transformToByteArray());const h=Buffer.alloc(44);
  h.write('RIFF');h.writeUInt32LE(pcm.length+36,4);h.write('WAVEfmt ',8);h.writeUInt32LE(16,16);h.writeUInt16LE(1,20);h.writeUInt16LE(1,22);h.writeUInt32LE(16000,24);h.writeUInt32LE(32000,28);h.writeUInt16LE(2,32);h.writeUInt16LE(16,34);h.write('data',36);h.writeUInt32LE(pcm.length,40);await writeFile(file,Buffer.concat([h,pcm]));
 }
 const wav=await readFile(file);manifest.items.push({id:c.id,text:c.input.utterance,file,sha256:createHash('sha256').update(wav).digest('hex')});
 await writeFile(`${dir}/manifest.json`,JSON.stringify(manifest,null,2));
}
console.log(JSON.stringify({files:manifest.items.length,synthetic:true}));
