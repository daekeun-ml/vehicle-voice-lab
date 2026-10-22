"""Freeze shared STT inputs: 79 source clips, clean A/B and 12-clip noise A/B."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import soundfile as sf
from scipy import signal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from experimental_denoise import denoise
OUT=ROOT/'output/asr-comparison'
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
def save(suite,item,condition,audio,meta=None):
    ident=f"{suite}--{item['id']}--{condition}"
    p=OUT/(ident+'.wav');sf.write(p,audio,16000,subtype='PCM_16')
    rows.append(dict(id=ident,suite=suite,caseId=item['id'],text=item['text'],
                     condition=condition,file=str(p.relative_to(ROOT)),
                     sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                     durationSeconds=len(audio)/16000,filter=meta))
for suite,folder in [('original31','vehicle-benchmark'),('hard48','vehicle-hard-v1')]:
    manifest=json.loads((ROOT/'output'/folder/'manifest.json').read_text())
    for idx,item in enumerate(manifest['items']):
        if 'text' not in item:
            item['text']=next(x['text'] for x in manifest['items'] if x['id']==item['id'].removesuffix('-noise'))
        x,sr=sf.read(ROOT/item['file'],dtype='float32')
        assert sr==16000 and x.ndim==1
        save(suite,item,'original',x)
        y,meta=denoise(x);save(suite,item,'original-denoised',y,meta)
        if idx>=6:continue
        # Synthetic stress conditions; shared pairs, never claimed as real cabin recordings.
        clean=np.pad(x,(6400,8000))
        for kind,db in [('colored',10),('white',0)]:
            seed=int(hashlib.sha256((suite+item['id']+kind).encode()).hexdigest()[:8],16)
            rng=np.random.default_rng(seed)
            noise=rng.standard_normal(len(clean))
            if kind=='colored':noise=signal.lfilter([1],[1,-.92],noise)
            active=np.abs(clean)>np.max(np.abs(clean))*.01
            noise*=np.sqrt(np.mean(clean[active]**2)/(np.mean(noise[active]**2)*10**(db/10)))
            mixed=clean+noise;mixed/=max(1,np.max(np.abs(mixed))/.95)
            stem=f'{kind}-{db}dB'
            save(suite,item,stem,mixed)
            y,meta=denoise(mixed);save(suite,item,stem+'-denoised',y,meta)
manifest=dict(version=1,synthetic=True,realCarNoise=False,noiseSubset='First six frozen cases from each suite; selected before STT results',
              algorithm='conservative-dd-wiener-v1',items=rows)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'{len(rows)} shared inputs × 4 STT models = {len(rows)*4} transcriptions')
