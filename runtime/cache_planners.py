"""Populate the reviewed planner allowlist before enabling offline swap loading."""
from huggingface_hub import snapshot_download
from model_server import PLANNERS
for repo,revision in PLANNERS.items():
 snapshot_download(repo,revision=revision,allow_patterns=['*.json','*.jinja','*.safetensors','*.model','tokenizer*'])
 print('Cached',repo,revision,flush=True)
