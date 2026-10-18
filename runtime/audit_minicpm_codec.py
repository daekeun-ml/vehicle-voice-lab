"""Reconstruct synthetic Korean speech without MiniCPM's text-to-token TTS."""
import json,pathlib,sys
import torch
import s3tokenizer
from stepaudio2 import Token2wav
from huggingface_hub import snapshot_download

root=pathlib.Path('/opt/vehicle-voice/minicpm-audit');out=root/('codec-command' if '--command' in sys.argv else 'codec');out.mkdir(exist_ok=True)
path=snapshot_download('openbmb/MiniCPM-o-4_5',revision='503e754207c94da6bb26850b4469f367c9ea3582',local_files_only=True)
codec=Token2wav(path+'/assets/token2wav')
audio=s3tokenizer.load_audio(str(root/('command-ko.wav' if '--command' in sys.argv else 'defrost-on.wav')),sr=16000)
mels,lengths=s3tokenizer.padding([s3tokenizer.log_mel_spectrogram(audio)])
with torch.inference_mode():tokens,lens=codec.audio_tokenizer.quantize(mels.cuda(),lengths.cuda())
ids=tokens[0,:int(lens[0])].tolist();results=[]
for label,reference in [('ko','reference-ko.wav'),('en','reference-neutral.wav')]:
    codec.cache=None
    with torch.inference_mode():wav=codec(ids,str(root/reference))
    name='reconstructed-'+label+'.wav';(out/name).write_bytes(wav);results.append({'reference':label,'file':name,'tokens':len(ids)})
(out/'report.json').write_text(json.dumps({'syntheticAudioOnly':True,'input':'조수석 온도를 이십오 도로 맞춰 주세요.' if '--command' in sys.argv else '앞유리 김서림 제거 켜줘.','bypassed':'MiniCPM TTS text-to-audio-token prediction','results':results},ensure_ascii=False,indent=2))
print(json.dumps(results),flush=True)
