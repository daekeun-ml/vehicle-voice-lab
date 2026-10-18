"""Fixed-text native TTS audit. Run on GPU while vehicle-minicpm is stopped."""
import importlib,json,pathlib,time,sys
import numpy as np
import soundfile as sf
import torch
import minicpm_server as worker

ROOT=pathlib.Path('/opt/vehicle-voice/minicpm-audit')
OUT=ROOT/('tts-sanity' if '--sanity' in sys.argv else 'tts');OUT.mkdir(exist_ok=True)
worker.load()
if not worker.status['ready']:raise RuntimeError(worker.status['error'])
model=worker.model
Params=importlib.import_module(type(model).__module__.rsplit('.',1)[0]+'.utils').TTSSamplingParams
cases=[('defrost','앞유리 김서림 제거 기능을 켰어요.'),('temperature','양쪽 온도를 이십삼 도로 맞췄어요.')]
profiles=[('en-reference',worker.ref_audio,'en',.8),('ko-reference',sf.read(ROOT/'reference-ko.wav',dtype='float32')[0],'en',.8),('ko-reference-zh-prompt',sf.read(ROOT/'reference-ko.wav',dtype='float32')[0],'zh',.8),('ko-reference-low-temperature',sf.read(ROOT/'reference-ko.wav',dtype='float32')[0],'en',.3)]
if '--sanity' in sys.argv:
    cases=[('english','The windshield defroster is on.'),('hello-ko','안녕하세요.'),('yes-ko','네.')];profiles=profiles[:1]
report={'revision':worker.REVISION,'syntheticAudioOnly':True,'seed':42,'method':'teacher forcing fixes the exact text; only native TTS generates speech','results':[]}
for profile,reference,language,temperature in profiles:
    for case,text in cases:
        model.reset_session(reset_token2wav_cache=True);model.init_token2wav_cache(reference)
        prompt=model.get_sys_prompt(ref_audio=reference,mode='audio_assistant',language=language)
        prompt['content'].append('다음 문장을 자연스러운 한국어로 정확히 읽으세요. 문장을 변경하거나 번역하지 마세요.')
        sid=profile+'-'+case;torch.manual_seed(42);audio=[];start=time.perf_counter()
        with torch.inference_mode():
            model.streaming_prefill(session_id=sid,msgs=[prompt],omni_mode=False,is_last_chunk=True)
            for wav,_ in model.streaming_generate(session_id=sid,generate_audio=True,use_tts_template=True,enable_thinking=False,teacher_forcing=True,teacher_forcing_text=text,tts_sampling_params=Params(temperature=temperature)):
                audio.append(wav.detach().float().cpu().numpy().reshape(-1))
        samples=np.concatenate(audio);name=profile+'-'+case+'.wav';sf.write(OUT/name,samples,24000,subtype='PCM_16')
        row={'profile':profile,'case':case,'text':text,'temperature':temperature,'seconds':len(samples)/24000,'elapsedMs':round((time.perf_counter()-start)*1000),'file':name}
        report['results'].append(row);(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(row,ensure_ascii=False),flush=True)
