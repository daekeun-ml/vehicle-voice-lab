#!/usr/bin/env bash
set -euo pipefail
if [ ! -x /opt/vehicle-node/bin/node ]; then
  build_dir=$(mktemp -d)
  cd "$build_dir"
  curl -fsS https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt -o sums.txt
  node_archive=$(awk '/node-v22\.[0-9]+\.[0-9]+-linux-x64.tar.xz$/ {print $2}' sums.txt)
  [[ "$node_archive" =~ ^node-v22\.[0-9]+\.[0-9]+-linux-x64\.tar\.xz$ ]]
  curl -fsS "https://nodejs.org/dist/latest-v22.x/$node_archive" -o "$node_archive"
  awk -v file="$node_archive" '$2==file' sums.txt | sha256sum -c -
  sudo mkdir -p /opt/vehicle-node
  sudo tar -xJf "$node_archive" -C /opt/vehicle-node --strip-components=1
fi
cd /opt/vehicle-web
export PATH=/opt/vehicle-node/bin:$PATH
npm ci --omit=dev --no-audit --no-fund
mkdir -p .runtime
sudo tee /etc/systemd/system/vehicle-web.service >/dev/null <<'UNIT'
[Unit]
Description=Vehicle voice shared CloudFront backend
After=network-online.target vehicle-core.service vehicle-whisper.service
Wants=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-web
EnvironmentFile=/etc/vehicle-web.env
ExecStart=/opt/vehicle-node/bin/node server.mjs
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vehicle-web/.runtime
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-web
/opt/vehicle-node/bin/node --version
