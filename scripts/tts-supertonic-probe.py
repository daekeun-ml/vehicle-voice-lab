import argparse,time,numpy as np
from supertonic import TTS
from tts_comparison_common import SUITE,new_report,save_report,save_row
p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True);args=p.parse_args()
np.random.seed(2026)
report=new_report('supertonic3','Supertone/supertonic-3','3cadd1ee6394adea1bd021217a0e650ede09a323',
                  {'device':'CPU','voice':'F1','language':'ko','steps':8,'speed':1.05,'intraOpThreads':4,'interOpThreads':1},
                  ['supertonic','onnxruntime','numpy','soundfile'])
start=time.perf_counter()
tts=TTS(model='supertonic-3',model_dir=args.model_dir,auto_download=False,intra_op_num_threads=4,inter_op_num_threads=1)
report['loadMs']=(time.perf_counter()-start)*1000
report['availableVoices']=tts.voice_style_names
style=tts.get_voice_style(voice_name='F1')
start=time.perf_counter();tts.synthesize('준비되었습니다.',voice_style=style,lang='ko',total_steps=8,speed=1.05)
report['warmupMs']=(time.perf_counter()-start)*1000;save_report(report)
for c in SUITE['cases']:
    start=time.perf_counter();wave,duration=tts.synthesize(c['text'],voice_style=style,lang='ko',total_steps=8,speed=1.05)
    ms=(time.perf_counter()-start)*1000
    save_row(report,c,wave,tts.sample_rate,ms)
