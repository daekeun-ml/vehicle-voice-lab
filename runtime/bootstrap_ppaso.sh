#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-voice
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
uv venv --python 3.12 ppaso-env
uv pip install --python ppaso-env/bin/python 'numpy==2.5.4' 'soundfile==0.14.0' 'python-mecab-ko==1.3.7' 'onnxruntime==1.31.0' huggingface_hub 'fastapi==0.159.1' uvicorn
sudo tee /etc/systemd/system/vehicle-tts-ppaso.service >/dev/null <<'UNIT'
[Unit]
Description=Ppaso Korean ONNX CPU TTS
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-voice
Environment=TTS_ENGINE=ppaso
Environment=HF_HOME=/opt/vehicle-voice/models
ExecStart=/opt/vehicle-voice/ppaso-env/bin/python -m uvicorn tts_worker:app --host 127.0.0.1 --port 9108
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-tts-ppaso
