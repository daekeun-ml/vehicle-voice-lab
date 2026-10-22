"""Re-transcribe synthetic audio saved by cloud-tts-smoke.mjs; diagnostic, not MOS."""
import json,re,unicodedata
from pathlib import Path
from math import gcd
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from transformers import AutoProcessor,AutoModelForSpeechSeq2Seq
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'.runtime/cloud-tts-validation.json').read_text())
repo='openai/whisper-large-v3-turbo';rev='41f01f3fe87f28c78e2fbf8b568835947dd65ed9'
processor=AutoProcessor.from_pretrained(repo,revision=rev)
model=AutoModelForSpeechSeq2Seq.from_pretrained(repo,revision=rev,dtype=torch.float16,attn_implementation='sdpa').to('cuda:0').eval()
rows=[]
for row in report['checks']:
    texts=[]
    for path in row['audioFiles']:
        a,sr=sf.read(ROOT/path);g=gcd(sr,16000)
        if sr!=16000:a=resample_poly(a,16000//g,sr//g)
        inp=processor(a,sampling_rate=16000,return_tensors='pt');inp['input_features']=inp['input_features'].to('cuda:0',dtype=torch.float16)
        with torch.inference_mode():tokens=model.generate(**inp,language='ko',task='transcribe',max_new_tokens=128,do_sample=False)
        texts.append(processor.batch_decode(tokens,skip_special_tokens=True)[0].strip())
    rows.append({'provider':row['provider'],'kind':row['kind'],'expected':row['expectedSpeech'],'transcript':' '.join(texts)})
    print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
(ROOT/'.runtime/cloud-tts-asr.json').write_text(json.dumps({'asrModel':repo,'asrRevision':rev,'humanListeningCompleted':False,'rows':rows},ensure_ascii=False,indent=2)+'\n')
