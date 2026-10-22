import argparse,time,numpy as np,torch,soundfile as sf
from qwen_tts import Qwen3TTSModel
from tts_comparison_common import SUITE,OUT,new_report,save_report,save_row
p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True);args=p.parse_args()
torch.set_num_threads(4);torch.manual_seed(2026);np.random.seed(2026)
report=new_report('qwen17','Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice','0c0e3051f131929182e2c023b9537f8b1c68adfe',
 {'device':'cuda:0','hardware':torch.cuda.get_device_name(0),'voice':'Sohee','language':'Korean','dtype':'BF16','attention':'sdpa','nonStreaming':True,'seed':2026},
 ['qwen-tts','torch','transformers','numpy','soundfile'])
start=time.perf_counter()
model=Qwen3TTSModel.from_pretrained(args.model_dir,device_map='cuda:0',dtype=torch.bfloat16,attn_implementation='sdpa')
torch.cuda.synchronize();report['loadMs']=(time.perf_counter()-start)*1000
report['modelCudaAllocatedMiB']=torch.cuda.memory_allocated()/2**20
start=time.perf_counter();model.generate_custom_voice(text='준비되었습니다.',language='Korean',speaker='Sohee',non_streaming_mode=True)
torch.cuda.synchronize();report['warmupMs']=(time.perf_counter()-start)*1000;save_report(report)
for c in SUITE['cases']:
 torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
 waves,sr=model.generate_custom_voice(text=c['text'],language='Korean',speaker='Sohee',non_streaming_mode=True)
 torch.cuda.synchronize();ms=(time.perf_counter()-start)*1000
 save_row(report,c,waves[0],sr,ms,{'cudaPeakAllocatedMiB':torch.cuda.max_memory_allocated()/2**20})
# A synthetic, non-test reference for CosyVoice; no real person's recording is used.
waves,sr=model.generate_custom_voice(text=SUITE['referenceText'],language='Korean',speaker='Sohee',non_streaming_mode=True)
ref=OUT/'cosyvoice-reference-qwen-sohee.wav';sf.write(ref,waves[0],sr,subtype='PCM_16')
report['referenceGenerated']={'file':str(ref.relative_to(OUT.parent.parent)),'text':SUITE['referenceText'],'sampleRate':sr,'source':'synthetic Qwen3-TTS Sohee preset'}
save_report(report)
