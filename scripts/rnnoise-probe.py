"""RNNoise comparator on exactly the PCM inputs saved by noise-reduction-probe.py.

Resample 16→48 kHz, apply RNNoise, compensate the measured fixed 20 ms output delay offline,
then resample back. The delay remains a live-deployment cost. The 960-sample offset was calibrated
on the two clean controls, then fixed for all noisy conditions; no per-case alignment.
"""
from pathlib import Path
from importlib.metadata import version
import json,time
import numpy as np
import soundfile as sf
from scipy import signal
from pyrnnoise import RNNoise
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/audio-front-end'
source=json.loads((OUT/'signal-metrics.json').read_text())
rows=[]
for item in source['rows']:
    x,sr=sf.read(ROOT/item['input']);ref,rs=sf.read(ROOT/item['reference']);assert sr==rs==16000
    started=time.perf_counter()
    up=signal.resample_poly(x,3,1)
    pcm=np.round(np.clip(np.pad(up,(0,960)),-1,1)*32767).astype(np.int16)
    engine=RNNoise(sample_rate=48000)
    frames=list(engine.denoise_chunk(pcm,partial=True))
    y=np.concatenate([f.reshape(-1) for _,f in frames]).astype(np.float64)/32768
    y=y[960:960+len(up)]
    if len(y)<len(up):y=np.pad(y,(0,len(up)-len(y)))
    y=signal.resample_poly(y,1,3)[:len(x)]
    assert len(y)==len(x) and np.isfinite(y).all()
    elapsed=(time.perf_counter()-started)*1000
    path=OUT/(item['id']+'-rnnoise.wav');sf.write(path,y,16000,subtype='PCM_16')
    def snr(a,b):return float(10*np.log10((np.sum(a*a)+1e-15)/(np.sum((b-a)**2)+1e-15)))
    before=snr(ref,x);after=snr(ref,y)
    rows.append({'id':item['id'],'condition':item['condition'],'reference':item['reference'],
                 'input':item['input'],'output':str(path.relative_to(ROOT)),
                 'snrBeforeDb':None if item['condition']=='clean' else before,'snrAfterDb':after,
                 'snrImprovementDb':None if item['condition']=='clean' else after-before,
                 'processingMs':elapsed,'speechProbabilityMean':float(np.mean([p for p,_ in frames]))})
    print(item['id'],rows[-1]['snrImprovementDb'],flush=True)
(OUT/'rnnoise-metrics.json').write_text(json.dumps({'algorithm':'RNNoise','wrapperVersion':version('pyrnnoise'),
 'delayCompensationSamplesAt48kHz':960,'delayBasis':'Fixed offset calibrated on clean controls, not optimized per noisy clip','sampleRateConversion':'scipy resample_poly 16→48→16 kHz',
 'scope':'Same synthetic two-clip engineering smoke test, not real cabin evaluation','rows':rows},ensure_ascii=False,indent=2)+'\n')
