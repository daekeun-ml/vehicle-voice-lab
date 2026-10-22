"""Conservative, utterance-level noise suppression prototype (not wired to the app).

Dependencies: numpy, scipy. Input/output: finite mono float audio at 16 kHz.
The entire utterance is needed to estimate noise; this is NOT a streaming filter.
No learned VAD, speaker separation, echo cancellation, or gain normalization.
"""
from dataclasses import asdict, dataclass
import time
import numpy as np
from scipy import signal
from scipy.ndimage import convolve1d

@dataclass(frozen=True)
class Config:
    sample_rate: int = 16000
    frame_length: int = 512       # 32 ms
    hop_length: int = 128         # 8 ms
    quiet_ratio: float = 0.40     # compared with 60th percentile frame power
    min_noise_seconds: float = 0.12
    max_attenuation_db: float = 9.0
    high_frequency_floor: float = 0.55  # protect weak consonant energy above 3 kHz
    decision_directed_alpha: float = 0.90
    suppress_smoothing: float = 0.85
    restore_smoothing: float = 0.15
    dry_mix: float = 0.15


def denoise(samples, sample_rate=16000, config=Config()):
    start=time.perf_counter()
    x=np.asarray(samples,dtype=np.float64)
    if x.ndim!=1 or not np.all(np.isfinite(x)):
        raise ValueError('Expected finite mono audio')
    if sample_rate!=16000 or config.sample_rate!=sample_rate:
        raise ValueError('This prototype supports 16 kHz only; resample before comparison')
    if len(x)>sample_rate*30:
        raise ValueError('Maximum utterance duration is 30 seconds')
    report={'algorithm':'conservative-dd-wiener-v1','config':asdict(config),
            'sampleCount':len(x),'sampleRate':sample_rate,'streaming':False}
    def finish(y,reason,**extra):
        report.update(mode=reason,**extra,processingMs=(time.perf_counter()-start)*1000)
        return np.asarray(y,dtype=np.float32),report
    if len(x)<config.frame_length*2:
        return finish(x,'bypass-too-short')
    if np.max(np.abs(x))<1e-7:
        return finish(x,'bypass-silence')
    frequencies,times,z=signal.stft(x,fs=sample_rate,window='hann',nperseg=config.frame_length,
                                   noverlap=config.frame_length-config.hop_length,
                                   boundary='zeros',padded=True)
    power=np.abs(z)**2
    band=(frequencies>=100)&(frequencies<=7500)
    energy=np.mean(power[band],axis=0)
    # Exclude padded boundaries: zeros introduced by STFT must not masquerade as noise-only speech pauses.
    valid=(times*sample_rate>=config.frame_length/2)&(times*sample_rate<=len(x)-config.frame_length/2)
    reference=np.percentile(energy[valid],60)
    quiet=valid&(energy<reference*config.quiet_ratio)
    required=max(3,int(np.ceil(config.min_noise_seconds*sample_rate/config.hop_length)))
    if np.count_nonzero(quiet)<required:
        return finish(x,'bypass-no-reliable-quiet-frames',noiseFrames=int(np.count_nonzero(quiet)))
    # A robust estimate from candidate pauses, with local frequency smoothing.
    # These are heuristic noise frames, not ground-truth speech/non-speech labels.
    noise=np.median(power[:,quiet],axis=1)
    noise=convolve1d(noise,np.array([1,2,3,2,1])/9,mode='nearest')
    eps=max(float(np.max(power))*1e-12,1e-18)
    if np.sum(noise)<np.sum(np.mean(power[:,valid],axis=1))*1e-7:
        return finish(x,'bypass-negligible-noise',noiseFrames=int(np.count_nonzero(quiet)))
    noise=np.maximum(noise,eps)
    floor=np.full(len(frequencies),10**(-config.max_attenuation_db/20))
    floor[frequencies>=3000]=np.maximum(floor[frequencies>=3000],config.high_frequency_floor)
    gains=np.ones_like(power);previous_gain=np.ones(len(frequencies));previous_post=np.ones(len(frequencies))
    for frame in range(power.shape[1]):
        if quiet[frame]:
            # Only adapt in likely pauses. Cap abrupt PSD updates from transient contamination.
            update=np.clip(power[:,frame],noise*.25,noise*4)
            noise=.96*noise+.04*update
        post=power[:,frame]/np.maximum(noise,eps)
        prior=config.decision_directed_alpha*previous_gain**2*previous_post+(1-config.decision_directed_alpha)*np.maximum(post-1,0)
        proposed=prior/(1+prior)
        proposed=convolve1d(proposed,np.array([1,2,3,2,1])/9,mode='nearest')
        proposed=np.maximum(proposed,floor)
        # Open quickly when speech begins; close slowly to avoid clipping weak endings.
        alpha=np.where(proposed>previous_gain,config.restore_smoothing,config.suppress_smoothing)
        gain=alpha*previous_gain+(1-alpha)*proposed
        if frame and energy[frame]>2*max(energy[frame-1],eps) and not quiet[frame]:
            gain=np.maximum(gain,.85)
        gains[:,frame]=gain
        previous_gain=gain;previous_post=post
    _,wet=signal.istft(z*gains,fs=sample_rate,window='hann',nperseg=config.frame_length,
                       noverlap=config.frame_length-config.hop_length,boundary=True)
    wet=wet[:len(x)]
    assert len(wet)==len(x)
    y=config.dry_mix*x+(1-config.dry_mix)*wet
    # Suppression never requires arbitrary loudness normalization. Do not amplify to equalize examples.
    # A peak guard only prevents new clipping if overlap-add creates an overshoot.
    limit=max(1.0,float(np.max(np.abs(x))))
    peak=float(np.max(np.abs(y)))
    if peak>limit:y*=limit/peak
    return finish(y,'filtered',noiseFrames=int(np.count_nonzero(quiet)),totalFrames=int(len(times)),
                  medianGain=float(np.median(gains)),minimumGain=float(np.min(gains)),
                  maxAtInput=float(np.max(np.abs(x))),maxAtOutput=float(np.max(np.abs(y))))
