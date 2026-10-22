"""Whisper re-transcription diagnostics for Kokoro and experimental noise suppression.

Kokoro uses authored input text; noise tests use clean-audio ASR output as a proxy,
NOT a human-verified transcript. Neither metric is a listening/MOS or vehicle score.
"""
import json,re,sys,time,unicodedata
from pathlib import Path
from math import gcd
from importlib.metadata import version
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import torch
from transformers import AutoProcessor,AutoModelForSpeechSeq2Seq
ROOT=Path(__file__).resolve().parents[1]
MODEL='openai/whisper-large-v3-turbo';REV='41f01f3fe87f28c78e2fbf8b568835947dd65ed9'
processor=AutoProcessor.from_pretrained(MODEL,revision=REV)
model=AutoModelForSpeechSeq2Seq.from_pretrained(MODEL,revision=REV,dtype=torch.float16,attn_implementation='sdpa').to('cuda:0').eval()
cache={}
def transcribe(path,language='ko'):
    key=(path,language)
    if key in cache:return cache[key]
    samples,sr=sf.read(ROOT/path)
    if samples.ndim==2:samples=samples.mean(axis=1)
    if sr!=16000:
        g=gcd(sr,16000);samples=resample_poly(samples,16000//g,sr//g)
    inputs=processor(samples,sampling_rate=16000,return_tensors='pt')
    inputs['input_features']=inputs['input_features'].to(model.device,dtype=torch.float16)
    started=time.perf_counter()
    with torch.inference_mode():out=model.generate(**inputs,language=language,task='transcribe',max_new_tokens=128,do_sample=False)
    text=processor.batch_decode(out,skip_special_tokens=True)[0].strip()
    result={'text':text,'ms':(time.perf_counter()-started)*1000};cache[key]=result
    print(path,text,flush=True);return result

def norm(text):
    text=unicodedata.normalize('NFKC',text).lower()
    for a,b in [('스물다섯','25'),('스물네','24'),('스물넷','24'),('이십사','24'),('이십오','25')]:text=text.replace(a,b)
    return ''.join(c for c in text if c.isalnum())

def distance(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=row
    return prev[-1]
meta={'model':MODEL,'revision':REV,'hardware':torch.cuda.get_device_name(0),'torch':version('torch'),
      'normalization':'NFKC, lowercase, alphanumeric only; explicit Korean number variants for 24 and 25',
      'humanListeningCompleted':False,'scope':'ASR diagnostic, not perceptual quality or end-to-end vehicle benchmark'}
p=ROOT/'research/kokoro-korean/probe.json';kokoro=json.loads(p.read_text())
rows=[]
for row in kokoro['rows']:
    result=transcribe(row['file']);a,b=norm(row['text']),norm(result['text'])
    rows.append({**row,'asr':result,'normalizedCharacterErrors':distance(a,b),'referenceCharacters':len(a),
                 'normalizedCer':distance(a,b)/max(1,len(a))})
english=transcribe(kokoro['englishControl']['file'],'en')
(ROOT/'research/kokoro-korean/asr-diagnostic.json').write_text(json.dumps({**meta,'rows':rows,'englishControl':english},ensure_ascii=False,indent=2)+'\n')
p=ROOT/'research/audio-front-end/signal-metrics.json';noise=json.loads(p.read_text());rows=[]
clean={r['source']:transcribe(r['reference']) for r in noise['rows'] if r['condition']=='clean'}
for row in noise['rows']:
    before=transcribe(row['input']);after=transcribe(row['output']);reference=clean[row['source']]['text'];a=norm(reference)
    rows.append({'id':row['id'],'condition':row['condition'],'filterMode':row['filter']['mode'],
                 'referenceProxy':reference,'before':before,'after':after,
                 'beforeAgreementErrorRate':distance(a,norm(before['text']))/max(1,len(a)),
                 'afterAgreementErrorRate':distance(a,norm(after['text']))/max(1,len(a))})
(ROOT/'research/audio-front-end/asr-diagnostic.json').write_text(json.dumps({**meta,
 'referenceBasis':'ASR output on clean reference; not independently human-transcribed ground truth', 'rows':rows},ensure_ascii=False,indent=2)+'\n')
rnn_path=ROOT/'research/audio-front-end/rnnoise-metrics.json'
if rnn_path.exists():
    rnn=json.loads(rnn_path.read_text());extra=[]
    for row in rnn['rows']:
        source_row=next(r for r in noise['rows'] if r['id']==row['id'])
        reference=clean[source_row['source']]['text'];a=norm(reference)
        result=transcribe(row['output'])
        extra.append({'id':row['id'],'condition':row['condition'],'referenceProxy':reference,'asr':result,
                      'agreementErrorRate':distance(a,norm(result['text']))/max(1,len(a))})
    (ROOT/'research/audio-front-end/rnnoise-asr.json').write_text(json.dumps({**meta,
        'referenceBasis':'ASR output on clean reference; not independently human-transcribed ground truth',
        'rows':extra},ensure_ascii=False,indent=2)+'\n')
