// Compare native speech with Korean TTS using exactly the same generated text.
// All input and output audio in this probe is synthetic.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {PollyClient,SynthesizeSpeechCommand} from '@aws-sdk/client-polly';
import {fromIni} from '@aws-sdk/credential-providers';
const base='http://localhost:8787',dir='output/minicpm-pronunciation';await mkdir(dir,{recursive:true});
const session=await(await fetch(base+'/api/session',{method:'POST'})).json();
const headers={'Content-Type':'application/json','X-Session-Id':session.id};
const input=await readFile('public/sample-command.wav');
const response=await fetch(base+'/api/s2s',{method:'POST',headers,body:JSON.stringify({comparisonOnly:true,audio:input.toString('base64'),language:'ko'}),signal:AbortSignal.timeout(120000)});
if(!response.ok)throw new Error(await response.text());
const events=(await response.text()).split('\n\n').filter(Boolean).map(block=>({event:block.split('\n')[0].slice(7),data:JSON.parse(block.split('\n')[1].slice(6))}));
const error=events.find(e=>e.event==='error');if(error)throw new Error(error.data.error);
const done=events.find(e=>e.event==='done')?.data.metrics;if(!done?.completed)throw new Error('Incomplete speech');
if(!/[가-힣]/.test(done.reply))throw new Error('No Korean generated text; pronunciation comparison is inconclusive');
function wav(pcm,rate){const h=Buffer.alloc(44);h.write('RIFF');h.writeUInt32LE(36+pcm.length,4);h.write('WAVEfmt ',8);h.writeUInt32LE(16,16);h.writeUInt16LE(1,20);h.writeUInt16LE(1,22);h.writeUInt32LE(rate,24);h.writeUInt32LE(rate*2,28);h.writeUInt16LE(2,32);h.writeUInt16LE(16,34);h.write('data',36);h.writeUInt32LE(pcm.length,40);return Buffer.concat([h,pcm]);}
function pcmOf(w){for(let at=12;at+8<=w.length;){const n=w.readUInt32LE(at+4);if(w.toString('ascii',at,at+4)==='data')return w.subarray(at+8,at+8+n);at+=8+n+(n%2);}throw new Error('WAV data missing');}
const native=Buffer.concat(events.filter(e=>e.event==='audio').map(e=>pcmOf(Buffer.from(e.data.audio,'base64'))));
await writeFile(dir+'/native-24k.wav',wav(native,24000));
const converted=spawnSync('ffmpeg',['-y','-i',dir+'/native-24k.wav','-ar','16000','-ac','1',dir+'/native.wav'],{encoding:'utf8'});if(converted.status!==0)throw new Error(converted.stderr);
const polly=new PollyClient({region:'ap-northeast-2',credentials:fromIni({profile:'game-forge'})});
const speech=await polly.send(new SynthesizeSpeechCommand({Text:done.reply,VoiceId:'Seoyeon',LanguageCode:'ko-KR',Engine:'neural',OutputFormat:'pcm',SampleRate:'16000'}));
const korean=Buffer.from(await speech.AudioStream.transformToByteArray());await writeFile(dir+'/polly.wav',wav(korean,16000));
const readings=[];
for(const name of ['native','polly']){
  const audio=await readFile(dir+'/'+name+'.wav'),form=new FormData();form.append('file',new Blob([audio],{type:'audio/wav'}),'speech.wav');
  const r=await fetch('http://127.0.0.1:19101/asr',{method:'POST',body:form,signal:AbortSignal.timeout(30000)});if(!r.ok)throw new Error(await r.text());
  readings.push({source:name,transcript:(await r.json()).text});
}
const report={at:new Date().toISOString(),syntheticAudioOnly:true,integrationVersion:done.integrationVersion,generatedText:done.reply,nativeSeconds:native.length/48000,pollySeconds:korean.length/32000,readings,note:'Independent ASR is a diagnostic indicator, not a human pronunciation rating. Listen to the paired WAV files.'};
await writeFile(dir+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
