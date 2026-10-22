#!/usr/bin/env bash
set -euo pipefail
cd /opt/vehicle-voice
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
uv venv --python 3.12 tts17-env
uv pip install --python tts17-env/bin/python 'qwen-tts==0.1.1' 'torch==2.14.1' 'transformers==4.57.3' accelerate fastapi uvicorn soundfile
uv venv --python 3.12 supertonic-env
uv pip install --python supertonic-env/bin/python 'supertonic==1.3.1' fastapi uvicorn soundfile huggingface_hub
for engine in qwen17 supertonic; do
  env_dir=tts17-env; port=9106
  if [ "$engine" = supertonic ]; then env_dir=supertonic-env; port=9107; fi
  sudo tee "/etc/systemd/system/vehicle-tts-${engine}.service" >/dev/null <<EOF
[Unit]
Description=Vehicle Korean TTS ${engine}
After=network-online.target
Wants=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-voice
Environment=TTS_ENGINE=${engine}
Environment=HF_HOME=/opt/vehicle-voice/models
Environment=TOKENIZERS_PARALLELISM=false
ExecStart=/opt/vehicle-voice/${env_dir}/bin/python -m uvicorn tts_worker:app --host 127.0.0.1 --port ${port}
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
done
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-tts-qwen17 vehicle-tts-supertonic
