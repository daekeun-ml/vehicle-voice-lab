"""Install isolated STT evaluation service; resume saved rows without changing public sessions."""
from pathlib import Path
import json, subprocess, tarfile

ROOT=Path(__file__).resolve().parents[1]
state=json.loads((ROOT/'.runtime/aws.json').read_text())
options=['-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key')]
host='ubuntu@'+state['publicIp']
def ssh(command):
    return subprocess.run(['ssh',*options,host,command],check=True)
def upload(source,target):
    subprocess.run(['scp',*options,str(source),host+':'+target],check=True)

ssh('if systemctl is-active --quiet vehicle-asr-run; then echo "STT evaluator already active" >&2; exit 1; fi')
manifest=json.loads((ROOT/'output/asr-comparison/manifest.json').read_text())
files=list(ROOT.glob('*.mjs'))+[ROOT/p for p in [
    'package.json','package-lock.json','model-catalog.json','scripts/run-asr-comparison.mjs',
    'scripts/vehicle-benchmark-cases.mjs','research/vehicle-hard-v1/cases.json',
    'output/asr-comparison/manifest.json']]
files += [ROOT/item['file'] for item in manifest['items']]
bundle=ROOT/'.runtime/asr-benchmark.tar.gz'
with tarfile.open(bundle,'w:gz') as tar:
    for p in files:tar.add(p,arcname=str(p.relative_to(ROOT)))
upload(bundle,'/tmp/asr-benchmark.tar.gz')
ssh('sudo mkdir -p /opt/vehicle-asr-benchmark && sudo chown ubuntu:ubuntu /opt/vehicle-asr-benchmark && '
    'tar xzf /tmp/asr-benchmark.tar.gz -C /opt/vehicle-asr-benchmark && '
    'mkdir -p /opt/vehicle-asr-benchmark/.runtime /opt/vehicle-asr-benchmark/research/asr-comparison && '
    'install -m 600 /opt/vehicle-benchmark/.runtime/benchmark-fixture.key /opt/vehicle-asr-benchmark/.runtime/benchmark-fixture.key && '
    'sudo sh -c "sed s/PORT=8788/PORT=8789/ /etc/vehicle-benchmark-api.env > /etc/vehicle-asr-benchmark.env" && '
    'sudo chmod 600 /etc/vehicle-asr-benchmark.env && '
    'cd /opt/vehicle-asr-benchmark && PATH=/opt/vehicle-node/bin:$PATH npm ci --omit=dev --no-audit --no-fund')
for name,command,env in [
    ('vehicle-asr-api','server.mjs','EnvironmentFile=/etc/vehicle-asr-benchmark.env'),
    ('vehicle-asr-run','scripts/run-asr-comparison.mjs','Environment=ASR_BENCH_BASE=http://127.0.0.1:8789')]:
    unit=f'''[Unit]
Description=Vehicle STT comparison {name}
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-asr-benchmark
{env}
ExecStart=/opt/vehicle-node/bin/node {command}
Restart=no
NoNewPrivileges=true
PrivateTmp=true
'''
    p=ROOT/'.runtime'/f'{name}.service';p.write_text(unit);upload(p,'/tmp/'+p.name)
    ssh(f'sudo install -m 644 /tmp/{p.name} /etc/systemd/system/{p.name}')
ssh('if [ ! -e /opt/vehicle-web/research/asr-comparison ]; then '
    'ln -s /opt/vehicle-asr-benchmark/research/asr-comparison /opt/vehicle-web/research/asr-comparison; '
    'else test "$(readlink -f /opt/vehicle-web/research/asr-comparison)" = /opt/vehicle-asr-benchmark/research/asr-comparison; fi')
ssh('sudo systemctl daemon-reload && sudo systemctl stop vehicle-minicpm && '
    'sudo systemctl restart vehicle-asr-api && sudo systemctl start vehicle-asr-run')
print('STT evaluation started. After completion restore vehicle-minicpm and verify GPU memory/health.')
