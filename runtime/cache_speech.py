from huggingface_hub import snapshot_download
from concurrent.futures import ThreadPoolExecutor
SPECS=[
 ('Qwen/Qwen3-Omni-30B-A3B-Instruct','26291f793822fb6be9555850f06dfe95f2d7e695',['*.json','*.safetensors','*.model','tokenizer*']),
 ('stepfun-ai/Step-Audio-2-mini','e36fdd5d71e0ea22f09dd94bbab9bfc544ca1e36',None),
 ('XiaomiMiMo/MiMo-Audio-7B-Instruct','c359441c22c2a1c74be5f99a91e83392680e9cc8',['*.json','*.safetensors','*.model','tokenizer*']),
 ('XiaomiMiMo/MiMo-Audio-Tokenizer','5df9914f72d3acda1320d7fecde7d91622edb0c1',['*.json','*.safetensors','*.pt','*.model']),
 ('kyutai/moshiko-pytorch-bf16','2bfc9ae6e89079a5cc7ed2a68436010d91a3d289',['model.safetensors','tokenizer_spm_32k_3.model','tokenizer-e351c8d8-checkpoint125.safetensors','config.json']),
]
def run(spec):
 repo,rev,patterns=spec;print('START',repo,flush=True);path=snapshot_download(repo,revision=rev,allow_patterns=patterns);print('CACHED',repo,path,flush=True)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,SPECS))
