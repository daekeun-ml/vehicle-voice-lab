#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-speech
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
uv venv --python 3.12 asr-env
uv pip install --python asr-env/bin/python 'qwen-asr==0.0.6' 'torch==2.14.1' 'transformers==4.57.6' fastapi uvicorn python-multipart soundfile
export HF_HOME=/opt/vehicle-speech/models
asr-env/bin/hf download Qwen/Qwen3-ASR-0.6B --revision 5eb144179a02acc5e5ba31e748d22b0cf3e303b0
asr-env/bin/hf download Qwen/Qwen3-ASR-1.7B --revision 7278e1e70fe206f11671096ffdd38061171dd6e5
uv pip freeze --python asr-env/bin/python > asr-requirements.lock
bash /opt/vehicle-speech/bootstrap_asr_services.sh
sudo systemctl restart vehicle-speech
