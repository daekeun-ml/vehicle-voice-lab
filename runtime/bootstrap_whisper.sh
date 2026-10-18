#!/usr/bin/env bash
set -euo pipefail
sudo tee /etc/systemd/system/vehicle-whisper.service >/dev/null <<'UNIT'
[Unit]
Description=Vehicle Korean Whisper ASR
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-voice
Environment=HF_HOME=/opt/vehicle-voice/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-voice/core-env/bin/python -m uvicorn whisper_server:app --host 127.0.0.1 --port 9105
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-whisper
