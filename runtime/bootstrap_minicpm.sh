#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-voice
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
if [ ! -x minicpm-env/bin/python ]; then uv venv --python 3.12 minicpm-env; fi
uv pip install --python minicpm-env/bin/python torch==2.8.0 torchaudio==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python minicpm-env/bin/python 'transformers==4.51.0' 'minicpmo-utils[all]==1.0.6' 'stepaudio2-minicpmo==0.1.1' accelerate fastapi uvicorn python-multipart soundfile 'numpy<2' sentencepiece
echo 'MiniCPM environment installed'

# Prerequisites: minicpm_server.py and a synthetic mono 16kHz reference-neutral.wav
test -f minicpm_server.py
test -f reference-neutral.wav
sudo tee /etc/systemd/system/vehicle-minicpm.service >/dev/null <<'UNIT'
[Unit]
Description=MiniCPM speech research worker
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-voice
Environment=HF_HOME=/opt/vehicle-voice/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-voice/minicpm-env/bin/python -m uvicorn minicpm_server:app --host 127.0.0.1 --port 9103
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-minicpm
