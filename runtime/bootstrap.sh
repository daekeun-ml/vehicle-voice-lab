#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-voice
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv ffmpeg libsndfile1 sox
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
BASE_PYTHON=/opt/pytorch/bin/python
if [ ! -x "$BASE_PYTHON" ]; then BASE_PYTHON=$(find /opt -path '*/bin/python' -type f 2>/dev/null | head -1); fi
if [ -z "$BASE_PYTHON" ]; then BASE_PYTHON=python3; fi
uv venv --system-site-packages --python "$BASE_PYTHON" core-env
uv venv --system-site-packages --python "$BASE_PYTHON" tts-env
uv pip install --python core-env/bin/python 'transformers==5.20.0' accelerate fastapi uvicorn python-multipart soundfile librosa 'xgrammar==0.2.8' 'bitsandbytes==0.49.2'
uv pip install --python tts-env/bin/python qwen-tts accelerate fastapi uvicorn python-multipart soundfile
HF_HOME=/opt/vehicle-voice/models core-env/bin/python cache_planners.py
for role in core tts; do
  port=9101; [ "$role" = tts ] && port=9102
  sudo tee /etc/systemd/system/vehicle-${role}.service >/dev/null <<EOF
[Unit]
Description=Vehicle voice ${role} model worker
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-voice
Environment=MODEL_ROLE=${role}
Environment=HF_HOME=/opt/vehicle-voice/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-voice/${role}-env/bin/python -m uvicorn model_server:app --host 127.0.0.1 --port ${port}
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
done
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-core vehicle-tts
echo 'BOOTSTRAP COMPLETE'
