"""Shared recording helpers for isolated TTS comparisons."""
from pathlib import Path
import hashlib,json,time,platform,resource
from importlib.metadata import version,PackageNotFoundError
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/tts-comparison'
SUITE=json.loads((OUT/'cases.json').read_text())

def new_report(model,repo,revision,configuration,packages):
    versions={}
    for p in packages:
        try:versions[p]=version(p)
        except PackageNotFoundError:versions[p]=None
    return {'model':model,'repo':repo,'revision':revision,'suiteId':SUITE['suiteId'],
            'configuration':configuration,'versions':versions,'python':platform.python_version(),
            'timingBasis':'whole utterance synthesis completion, not first streamed audio; excludes model load and disk write',
            'humanListeningCompleted':False,'appIntegration':False,'rows':[]}

def save_report(report):
    (OUT/(report['model']+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

def save_row(report,case,wave,sample_rate,ms,extra=None):
    x=np.asarray(wave,dtype=np.float32).squeeze()
    if x.ndim!=1 or not np.isfinite(x).all() or len(x)==0:raise ValueError('Invalid synthesized audio')
    folder=OUT/report['model'];folder.mkdir(exist_ok=True)
    file=folder/(case['id']+'.wav')
    sf.write(file,x,sample_rate,subtype='PCM_16')
    row={**case,'file':str(file.relative_to(ROOT)),'sampleRate':sample_rate,
         'durationSeconds':len(x)/sample_rate,'audioValid':bool(len(x)>=sample_rate*.1 and np.max(np.abs(x))>1e-5),'synthesisMs':ms,'realTimeFactor':ms/1000/(len(x)/sample_rate),
         'peakBeforePCM':float(np.max(np.abs(x))),'samplesOutsidePCMRange':int(np.sum(np.abs(x)>1)),
         'processLifetimePeakRssMiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
         'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),**(extra or {})}
    report['rows'].append(row);save_report(report)
    print(report['model'],case['id'],round(ms),'ms',round(row['durationSeconds'],2),'s',flush=True)
