"""Offline A/B probe with known clean references and synthetic noise, not real car audio."""
from pathlib import Path
import json,time,sys,hashlib
from importlib.metadata import version
import numpy as np
from scipy import signal
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from experimental_denoise import denoise
OUT=ROOT/'research/audio-front-end'
OUT.mkdir(parents=True,exist_ok=True)
SR=16000
SOURCES=[('command','public/sample-command.wav'),('defrost-reply','public/benchmark-audio/qwen35-4b-defrost-on-reply.wav')]

def snr(reference,estimate):
    return float(10*np.log10((np.sum(reference**2)+1e-15)/(np.sum((estimate-reference)**2)+1e-15)))

def sisdr(reference,estimate):
    reference=reference-reference.mean();estimate=estimate-estimate.mean()
    target=reference*np.dot(reference,estimate)/(np.dot(reference,reference)+1e-15)
    return float(10*np.log10((np.sum(target**2)+1e-15)/(np.sum((estimate-target)**2)+1e-15)))

def save(name,x):
    p=OUT/(name+'.wav');sf.write(p,x,SR,subtype='PCM_16');return str(p.relative_to(ROOT))

report={'algorithm':'conservative-dd-wiener-v1','noise':'synthetic, NOT recorded cabin/road noise',
        'datasetScope':'2 existing synthetic speech clips; engineering smoke test, not a performance benchmark',
        'versions':{k:version(k) for k in ['numpy','scipy','soundfile']},'rows':[]}
for name,path in SOURCES:
    clean,sr=sf.read(ROOT/path)
    if clean.ndim!=1:raise ValueError('Expected mono source')
    if sr!=SR:
        from math import gcd
        g=gcd(sr,SR);clean=signal.resample_poly(clean,SR//g,sr//g)
    # Deliberately add real zero-valued pauses. The filter never receives these masks or clean reference.
    clean=np.pad(clean,(int(.4*SR),int(.5*SR)))
    clean=clean/max(1,float(np.max(np.abs(clean)))/.60)
    base=save(name+'-clean',clean)
    filtered,meta=denoise(clean)
    f=save(name+'-clean-filtered',filtered)
    report['rows'].append({'id':name+'-clean','source':path,'reference':base,'input':base,'output':f,
                           'condition':'clean','snrBeforeDb':None,'snrAfterDb':snr(clean,filtered),
                           'siSdrAfterDb':sisdr(clean,filtered),'filter':meta})
    for kind in ['stationary-colored','colored-plus-bursts']:
        for level in [20,10,0]:
            rng=np.random.default_rng(4821)
            noise=rng.standard_normal(len(clean))
            noise=signal.lfilter([1],[1,-.92],noise)
            noise/=np.sqrt(np.mean(noise**2))
            tm=np.arange(len(clean))/SR
            noise+=.45*np.sin(2*np.pi*100*tm)+.2*np.sin(2*np.pi*200*tm)
            if kind=='colored-plus-bursts':
                for position in [.35,.60,.80]:
                    offset=int(position*len(clean));n=min(int(.09*SR),len(clean)-offset)
                    noise[offset:offset+n]+=5*rng.standard_normal(n)*np.hanning(n)
            active=np.abs(clean)>np.max(np.abs(clean))*.01
            scale=np.sqrt(np.mean(clean[active]**2)/(np.mean(noise[active]**2)*10**(level/10)))
            noise*=scale;mixture=clean+noise
            # Scale the entire pair identically to prevent clipping without changing its SNR.
            headroom=max(1,np.max(np.abs(mixture))/.95)
            reference=clean/headroom;mixture/=headroom
            filtered,meta=denoise(mixture)
            stem=f'{name}-{kind}-{level}dB'
            inp=save(stem+'-raw',mixture);out=save(stem+'-filtered',filtered)
            ref=save(stem+'-reference',reference)
            before=snr(reference,mixture);after=snr(reference,filtered)
            report['rows'].append({'id':stem,'source':path,'reference':ref,'input':inp,'output':out,
                                   'condition':kind,'targetActiveSnrDb':level,'snrBeforeDb':before,'snrAfterDb':after,
                                   'snrImprovementDb':after-before,'siSdrBeforeDb':sisdr(reference,mixture),
                                   'siSdrAfterDb':sisdr(reference,filtered),'filter':meta})
for r in report['rows']:
    r['inputSha256']=hashlib.sha256((ROOT/r['input']).read_bytes()).hexdigest()
report['createdAt']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
(OUT/'signal-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for r in report['rows']:print(r['id'],r['filter']['mode'],'SNR improvement',r.get('snrImprovementDb'),flush=True)
