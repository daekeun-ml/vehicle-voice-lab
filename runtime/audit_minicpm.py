"""GPU-only controlled integration audit using synthetic fixtures.

Stop vehicle-minicpm before running to avoid loading a second model on the GPU.
The caller must restart that service after this process exits.
"""
import hashlib,json,pathlib,time
import numpy as np
import soundfile as sf
import torch
import minicpm_server as worker

ROOT=pathlib.Path('/opt/vehicle-voice/minicpm-audit')
worker.load()
if not worker.status['ready']:raise RuntimeError(worker.status['error'])
model=worker.model
report={'revision':worker.REVISION,'syntheticAudioOnly':True,'results':[]}
cases=[('math-en','en'),('math-ko','ko'),('command-ko','ko')]
profiles=['legacy','official','neutral-reference']
for profile in profiles:
    for case,language in cases:
        samples,rate=sf.read(ROOT/(case+'.wav'),dtype='float32')
        assert rate==16000 and samples.ndim==1
        reference,_=sf.read(ROOT/'reference-legacy.wav',dtype='float32')
        if profile=='neutral-reference':reference,_=sf.read(ROOT/'reference-neutral.wav',dtype='float32')
        model.reset_session(reset_token2wav_cache=True)
        model.init_token2wav_cache(reference)
        prompt=model.get_sys_prompt(ref_audio=reference,mode='omni' if profile=='legacy' else 'audio_assistant',language='en')
        prompt['content'].append('You are a brief speech research assistant. You have NO vehicle tools. Never claim to change any vehicle setting. Answer in one short sentence. '+('Try to respond in Korean; this is an unsupported language experiment.' if language=='ko' else 'Respond in English.'))
        sid=profile+'-'+case;start=time.perf_counter();first=None;text='';chunks=0
        torch.manual_seed(42)
        with torch.inference_mode():
            model.streaming_prefill(session_id=sid,msgs=[prompt],omni_mode=False,is_last_chunk=True)
            for pos in range(0,len(samples),16000):
                chunk=samples[pos:pos+16000];last=pos+16000>=len(samples)
                if profile!='legacy' and last and len(chunk)<16000:chunk=np.pad(chunk,(0,16000-len(chunk)))
                model.streaming_prefill(session_id=sid,msgs=[{'role':'user','content':[chunk]}],omni_mode=False,is_last_chunk=last)
            args={'do_sample':False,'max_new_tokens':96} if profile=='legacy' else {'do_sample':True,'max_new_tokens':512,'length_penalty':1.1}
            for wav,piece in model.streaming_generate(session_id=sid,generate_audio=True,use_tts_template=True,enable_thinking=False,**args):
                first=first or round((time.perf_counter()-start)*1000);text+=piece;chunks+=1
        row={'profile':profile,'case':case,'inputSamples':len(samples),'sha256':hashlib.sha256((ROOT/(case+'.wav')).read_bytes()).hexdigest(),'text':text,'chunks':chunks,'firstAudioMs':first,'totalMs':round((time.perf_counter()-start)*1000)}
        report['results'].append(row);(ROOT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(row,ensure_ascii=False),flush=True)
