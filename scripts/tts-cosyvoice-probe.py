import argparse,time,sys,subprocess,hashlib
from pathlib import Path
import numpy as np,torch
from tts_comparison_common import ROOT,OUT,SUITE,new_report,save_report,save_row
p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True);p.add_argument('--source-dir',required=True);args=p.parse_args()
src=Path(args.source_dir)
sys.path[:0]=[str(src),str(src/'third_party/Matcha-TTS')]
from cosyvoice.cli.cosyvoice import AutoModel
reference=OUT/'cosyvoice-reference-qwen-sohee.wav'
assert reference.exists(),'Run the Qwen probe first to create the synthetic reference.'
torch.set_num_threads(4);torch.manual_seed(2026);np.random.seed(2026)
report=new_report('cosyvoice3','FunAudioLLM/Fun-CosyVoice3-0.5B-2512','29e01c4e8d000f4bcd70751be16fa94bf3d85a18',
 {'device':'cuda:0','hardware':torch.cuda.get_device_name(0),'fp16':True,'loadTRT':False,'loadVLLM':False,
  'stream':False,'textFrontend':False,'reference':str(reference.relative_to(ROOT)),
  'referenceText':SUITE['referenceText'],'referenceSha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
  'referenceSource':'Qwen3-TTS-1.7B Sohee synthetic voice, not a human recording'},
 ['torch','torchaudio','transformers','onnxruntime-gpu','openai-whisper','numpy','soundfile'])
report['sourceRevision']=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()
report['submodules']=subprocess.check_output(['git','-C',str(src),'submodule','status','--recursive'],text=True).strip()
start=time.perf_counter();model=AutoModel(model_dir=args.model_dir,load_trt=False,load_vllm=False,fp16=True)
torch.cuda.synchronize();report['loadMs']=(time.perf_counter()-start)*1000
report['modelCudaAllocatedMiB']=torch.cuda.memory_allocated()/2**20
prompt='You are a helpful assistant.<|endofprompt|>'+SUITE['referenceText']
start=time.perf_counter()
model.add_zero_shot_spk(prompt,str(reference),'vehicle-synthetic')
torch.cuda.synchronize();report['referenceEncodingMs']=(time.perf_counter()-start)*1000

def synthesize(text):
 outputs=list(model.inference_zero_shot(text,prompt,str(reference),zero_shot_spk_id='vehicle-synthetic',stream=False,text_frontend=False))
 return torch.cat([o['tts_speech'] for o in outputs],dim=1).detach().cpu().numpy().squeeze()
start=time.perf_counter();synthesize('준비되었습니다.');torch.cuda.synchronize()
report['warmupMs']=(time.perf_counter()-start)*1000;save_report(report)
for c in SUITE['cases']:
 torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
 wave=synthesize(c['text']);torch.cuda.synchronize();ms=(time.perf_counter()-start)*1000
 save_row(report,c,wave,model.sample_rate,ms,{'cudaPeakAllocatedMiB':torch.cuda.max_memory_allocated()/2**20})
