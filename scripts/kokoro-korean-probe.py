"""Isolated Kokoro Korean probe. Does not change the app's TTS provider.

Dependencies: kokoro==0.9.4, soundfile, torch, huggingface_hub.
The eSpeak G2P below is an experimental phoneme adapter, not official Korean support.
"""
import json,time,platform,hashlib
from pathlib import Path
from importlib.metadata import version
import numpy as np
import soundfile as sf
import torch
from huggingface_hub import hf_hub_download
from kokoro import KModel,KPipeline
from misaki.espeak import EspeakG2P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/kokoro-korean'
OUT.mkdir(parents=True,exist_ok=True)
REPO='hexgrad/Kokoro-82M'
REV='f3ff3571791e39611d31c381e3a41a3af07b4987'
TEXTS=[('greeting','안녕하세요.'),('temperature','조수석 온도를 스물네 도로 맞췄어요.'),
       ('negation','에어컨을 끄지 않았어요.'),('seat-scope','운전석만 낮추고 조수석은 그대로 뒀어요.')]
report={'repo':REPO,'revision':REV,'python':platform.python_version(),
        'versions':{x:version(x) for x in ['kokoro','misaki','torch','transformers','soundfile']},
        'device':'cuda:0' if torch.cuda.is_available() else 'cpu',
        'hardware':torch.cuda.get_device_name(0) if torch.cuda.is_available() else platform.processor(),
        'officialKoreanMode':[],'rows':[],'humanListeningCompleted':False}
for code in ['ko','k']:
    try:
        KPipeline(lang_code=code,repo_id=REPO,model=False)
        report['officialKoreanMode'].append({'lang_code':code,'accepted':True})
    except Exception as e:
        report['officialKoreanMode'].append({'lang_code':code,'accepted':False,'error':type(e).__name__+': '+str(e)})
config=hf_hub_download(REPO,'config.json',revision=REV)
weights=hf_hub_download(REPO,'kokoro-v1_0.pth',revision=REV)
started=time.perf_counter()
model=KModel(repo_id=REPO,config=config,model=weights).to(report['device']).eval()
report['loadSeconds']=time.perf_counter()-started
# French mode avoids an English spaCy model download; we bypass its G2P below.
# generate_from_tokens accepts phonemes and a loaded voice tensor directly.
pipe=KPipeline(lang_code='f',repo_id=REPO,model=model)
g2p=EspeakG2P('ko')
voices={name:torch.load(hf_hub_download(REPO,f'voices/{name}.pt',revision=REV),weights_only=True)
        for name in ['af_heart','jf_alpha']}
for sid,text in TEXTS:
    original,_=g2p(text)
    # Compact IPA affricates and approximate dark l; this is explicit adaptation, not a trained Korean voice.
    mapped=original.replace('dʑ','ʥ').replace('tɕ','ʨ').replace('ɫ','l')
    for adapter,phonemes in [('espeak-ko-raw',original),('espeak-ko-mapped',mapped)]:
        unsupported=sorted(set(phonemes)-set(model.vocab))
        for voice,pack in voices.items():
            start=time.perf_counter()
            with torch.inference_mode():
                results=list(pipe.generate_from_tokens(phonemes,voice=pack))
            samples=np.concatenate([r.audio.detach().cpu().numpy() for r in results])
            file=OUT/f'{sid}-{adapter}-{voice}.wav';sf.write(file,samples,24000,subtype='PCM_16')
            report['rows'].append({'id':sid,'text':text,'adapter':adapter,'voice':voice,
                                  'phonemes':phonemes,'unsupportedPhonemeCharacters':unsupported,
                                  'file':str(file.relative_to(ROOT)),'sampleRate':24000,'durationSeconds':len(samples)/24000,
                                  'inferenceSeconds':time.perf_counter()-start,'peak':float(np.max(np.abs(samples))),
                                  'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
            print(sid,adapter,voice,report['rows'][-1]['durationSeconds'],flush=True)
# Same model/voice, supported English pronunciation, as a synthesis sanity check.
english='The passenger temperature is now twenty four degrees.'
phones,_=EspeakG2P('en-us')(english)
with torch.inference_mode():audio=np.concatenate([r.audio.cpu().numpy() for r in pipe.generate_from_tokens(phones,voice=voices['af_heart'])])
file=OUT/'english-control-af_heart.wav';sf.write(file,audio,24000,subtype='PCM_16')
report['englishControl']={'text':english,'file':str(file.relative_to(ROOT)),'durationSeconds':len(audio)/24000}
(OUT/'probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Saved',OUT/'probe.json',flush=True)
