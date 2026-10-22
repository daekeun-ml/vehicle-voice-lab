"""Common Whisper re-transcription of the three TTS candidates. Not a MOS test."""
import json,time,re,unicodedata
from pathlib import Path
from math import gcd
from importlib.metadata import version
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from transformers import AutoProcessor,AutoModelForSpeechSeq2Seq
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/tts-comparison'
NAMES=['supertonic3','qwen17','cosyvoice3']
reports={n:json.loads((OUT/(n+'.json')).read_text()) for n in NAMES}
assert all(len(d['rows'])==8 for d in reports.values())
MODEL='openai/whisper-large-v3-turbo';REV='41f01f3fe87f28c78e2fbf8b568835947dd65ed9'
processor=AutoProcessor.from_pretrained(MODEL,revision=REV)
model=AutoModelForSpeechSeq2Seq.from_pretrained(MODEL,revision=REV,dtype=torch.float16,attn_implementation='sdpa').to('cuda:0').eval()

NUMBER_FORMS={'이십이점오':'22.5','스물두점오':'22.5','스물네':'24','스물넷':'24','이십사':'24',
              '열아홉':'19','십구':'19','스물일곱':'27','이십칠':'27','아홉단':'9단','구단':'9단','세단':'3단','삼단':'3단'}
def words(text):
    text=re.sub(r'\s+','',unicodedata.normalize('NFKC',text).lower())
    for a,b in sorted(NUMBER_FORMS.items(),key=lambda kv:-len(kv[0])):text=text.replace(a,b)
    return text

def normalize(text):
    text=words(text)
    return ''.join(c for i,c in enumerate(text) if c.isalnum() or (c=='.' and i and i+1<len(text) and text[i-1].isdigit() and text[i+1].isdigit()))

def errors(a,b):
    p=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        q=[i]
        for j,y in enumerate(b,1):q.append(min(q[-1]+1,p[j]+1,p[j-1]+(x!=y)))
        p=q
    return p[-1]

output={'asrModel':MODEL,'asrRevision':REV,'hardware':torch.cuda.get_device_name(0),
        'versions':{p:version(p) for p in ['torch','transformers','scipy']},
        'scope':'8 fixed authored TTS inputs, one generation each; ASR proxy only, no human listening/MOS',
        'numberNormalization':NUMBER_FORMS,'rows':[]}
for name,report in reports.items():
    for row in report['rows']:
        x,sr=sf.read(ROOT/row['file']);g=gcd(sr,16000)
        if sr!=16000:x=resample_poly(x,16000//g,sr//g)
        skipped=len(x)<1600
        if skipped:
            heard=''
        else:
            inputs=processor(x,sampling_rate=16000,return_tensors='pt')
            inputs['input_features']=inputs['input_features'].to(model.device,dtype=torch.float16)
            with torch.inference_mode():tokens=model.generate(**inputs,language='ko',task='transcribe',max_new_tokens=128,do_sample=False)
            heard=processor.batch_decode(tokens,skip_special_tokens=True)[0].strip()
        a,b=normalize(row['text']),normalize(heard)
        expectedNumbers=re.findall(r'\d+(?:\.\d+)?',words(row['text']))
        actualNumbers=re.findall(r'\d+(?:\.\d+)?',words(heard))
        output['rows'].append({'model':name,'id':row['id'],'text':row['text'],'transcript':heard,'file':row['file'],
                               'asrSkipped':skipped,'skipReason':'audio shorter than 100ms' if skipped else None,
                               'normalizedExact':a==b,'characterErrors':errors(a,b),'referenceCharacters':len(a),
                               'normalizedCer':errors(a,b)/max(1,len(a)),
                               'numberSequenceExpected':expectedNumbers,'numberSequenceHeard':actualNumbers,
                               'numberSequenceMatches':expectedNumbers==actualNumbers})
        (OUT/'asr-diagnostic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print(name,row['id'],heard,flush=True)
reference=reports['qwen17']['referenceGenerated'];x,sr=sf.read(ROOT/reference['file']);g=gcd(sr,16000)
x=resample_poly(x,16000//g,sr//g);inputs=processor(x,sampling_rate=16000,return_tensors='pt')
inputs['input_features']=inputs['input_features'].to(model.device,dtype=torch.float16)
with torch.inference_mode():tokens=model.generate(**inputs,language='ko',task='transcribe',max_new_tokens=128,do_sample=False)
output['cosyvoiceReferenceCheck']={'text':reference['text'],'transcript':processor.batch_decode(tokens,skip_special_tokens=True)[0].strip()}
(OUT/'asr-diagnostic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
