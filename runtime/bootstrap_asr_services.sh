#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-speech
for pair in 'qwen3-asr-06b 9116' 'qwen3-asr-17b 9117'; do
  read -r model port <<< "$pair"
  sudo tee "/etc/systemd/system/vehicle-${model}.service" >/dev/null <<EOF
[Unit]
Description=Independent ${model} GPU ASR
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-speech
Environment=SPEECH_MODEL_ID=${model}
Environment=HF_HOME=/opt/vehicle-speech/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-speech/asr-env/bin/python -m uvicorn qwen_asr_worker:app --host 127.0.0.1 --port ${port}
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
done
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-qwen3-asr-06b vehicle-qwen3-asr-17b
