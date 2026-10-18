#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-speech
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv ffmpeg libsndfile1 sox git
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv venv --system-site-packages --python /opt/pytorch/bin/python omni-env
uv pip install --python omni-env/bin/python 'transformers==4.57.6' 'bitsandbytes==0.49.2' accelerate fastapi uvicorn python-multipart soundfile librosa httpx 'xgrammar==0.2.8' qwen-omni-utils
# Pin CUDA Torch explicitly; the DLAMI interpreter may not expose Torch.
uv pip install --python omni-env/bin/python torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
# Custom-code audio models need their own pinned Transformers runtime.
uv venv --system-site-packages --python /opt/pytorch/bin/python legacy-env
uv pip install --python legacy-env/bin/python 'transformers==4.49.0' accelerate fastapi uvicorn python-multipart soundfile librosa httpx s3tokenizer onnxruntime hyperpyyaml diffusers zhon sentencepiece sphn safetensors xgrammar==0.2.8
uv pip install --python legacy-env/bin/python torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python legacy-env/bin/python "https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3%2Bcu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl"
uv venv --system-site-packages --python /opt/pytorch/bin/python moshi-env
uv pip install --python moshi-env/bin/python --no-deps moshi==0.2.13
uv pip install --python moshi-env/bin/python fastapi uvicorn python-multipart soundfile librosa httpx sentencepiece sphn safetensors einops huggingface_hub aiohttp
uv pip install --python moshi-env/bin/python torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
if [ ! -d Step-Audio2 ]; then git clone https://github.com/stepfun-ai/Step-Audio2.git; fi
(cd Step-Audio2 && git checkout 76e272b56c3917a8d7188f18bbb5a65dfc8a0845)
if [ ! -d MiMo-Audio ]; then git clone https://github.com/XiaomiMiMo/MiMo-Audio.git; fi
(cd MiMo-Audio && git checkout 691ce54144a6844cc641fd96046a6ba20776c8b0)
sudo tee /etc/systemd/system/vehicle-speech.service >/dev/null <<EOF
[Unit]
Description=Swappable vehicle speech model worker
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-speech
Environment=HF_HOME=/opt/vehicle-speech/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-speech/omni-env/bin/python -m uvicorn speech_manager:app --host 127.0.0.1 --port 9104
Restart=on-failure
RestartSec=10
KillMode=control-group
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-speech
