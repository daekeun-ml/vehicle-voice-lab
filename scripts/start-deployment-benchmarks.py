"""Install a private benchmark API/release and start checkpointed 14-model evaluation.

The public app is not restarted. Only predefined fixtures are accepted by the
private loopback API. Credentials/fixture key are never included in the archive.
"""
from pathlib import Path
import json,subprocess,tarfile,secrets,os,hashlib
ROOT=Path(__file__).resolve().parents[1]
core=json.loads((ROOT/'.runtime/aws.json').read_text())
speech=json.loads((ROOT/'.runtime/speech-aws.json').read_text())
options=['-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key')]
host='ubuntu@'+core['publicIp']
def ssh(command):return subprocess.run(['ssh',*options,host,command],check=True)
def scp(source,target):subprocess.run(['scp',*options,str(source),host+':'+target],check=True)
# Refuse to replace a release while either evaluator is running.
ssh('if systemctl is-active --quiet vehicle-benchmark-run || systemctl is-active --quiet vehicle-benchmark-sonic; then echo "An evaluator is already running" >&2; exit 1; fi')
keyfile=ROOT/'.runtime/benchmark-fixture.key'
if not keyfile.exists():keyfile.write_text(secrets.token_urlsafe(48));keyfile.chmod(0o600)
files=list(ROOT.glob('*.mjs'))+[ROOT/p for p in ['package.json','package-lock.json','model-catalog.json',
 'scripts/run-deployment-benchmarks.mjs','scripts/vehicle-benchmark-cases.mjs','research/vehicle-hard-v1/cases.json']]
for folder in ['output/vehicle-benchmark','output/vehicle-hard-v1']:
 manifest=ROOT/folder/'manifest.json';files.append(manifest)
 for item in json.loads(manifest.read_text())['items']:files.append(ROOT/item['file'])
bundle=ROOT/'.runtime/benchmark-release.tar.gz'
with tarfile.open(bundle,'w:gz') as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(ROOT)))
sha=hashlib.sha256(bundle.read_bytes()).hexdigest()
models=json.loads((ROOT/'model-catalog.json').read_text())['models']
ids=[m['id'] for m in models if m['status']=='ready' and (m['role']=='sllm' or m.get('audioPlanner') or m['id']=='minicpm-o45')]
assert len(ids)==13
runtime_env={'PORT':'8788','BIND_HOST':'127.0.0.1','AWS_CREDENTIAL_MODE':'instance','AWS_REGION':core['region'],
 'SONIC_REGION':'ap-northeast-1','SONIC_MODEL':'amazon.nova-2-5-sonic','CORE_URL':'http://127.0.0.1:9101',
 'TTS_URL':'http://127.0.0.1:9102','QWEN17_TTS_URL':'http://127.0.0.1:9106','SUPERTONIC_TTS_URL':'http://127.0.0.1:9107',
 'MINICPM_URL':'http://127.0.0.1:9103','WHISPER_URL':'http://127.0.0.1:9105','SPEECH_URL':'http://'+speech['privateIp']+':9204' if 'privateIp' in speech else 'http://'+json.loads((ROOT/'.runtime/cloud-deployment.json').read_text())['speechPrivateIp']+':9204',
 'BENCHMARK_FIXTURE_KEY':keyfile.read_text().strip()}
envfile=ROOT/'.runtime/benchmark-api.env';envfile.write_text('\n'.join(k+'='+v for k,v in runtime_env.items())+'\n');envfile.chmod(0o600)
ssh('sudo mkdir -p /opt/vehicle-benchmark && sudo chown ubuntu:ubuntu /opt/vehicle-benchmark')
scp(bundle,'/tmp/vehicle-benchmark-release.tar.gz');scp(envfile,'/tmp/vehicle-benchmark-api.env');scp(keyfile,'/tmp/vehicle-benchmark-fixture.key')
ssh('tar -xzf /tmp/vehicle-benchmark-release.tar.gz -C /opt/vehicle-benchmark && mkdir -p /opt/vehicle-benchmark/.runtime /opt/vehicle-benchmark/research/deployment-benchmarks && chmod 700 /opt/vehicle-benchmark/.runtime && install -m 600 /tmp/vehicle-benchmark-fixture.key /opt/vehicle-benchmark/.runtime/benchmark-fixture.key && sudo install -m 600 /tmp/vehicle-benchmark-api.env /etc/vehicle-benchmark-api.env && rm /tmp/vehicle-benchmark-api.env /tmp/vehicle-benchmark-fixture.key && cd /opt/vehicle-benchmark && PATH=/opt/vehicle-node/bin:$PATH npm ci --omit=dev --no-audit --no-fund')
ssh('if [ ! -e /opt/vehicle-web/research/deployment-benchmarks ]; then ln -s /opt/vehicle-benchmark/research/deployment-benchmarks /opt/vehicle-web/research/deployment-benchmarks; else test "$(readlink -f /opt/vehicle-web/research/deployment-benchmarks)" = /opt/vehicle-benchmark/research/deployment-benchmarks; fi')
api='''[Unit]
Description=Private vehicle benchmark API
After=network-online.target
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-benchmark
EnvironmentFile=/etc/vehicle-benchmark-api.env
ExecStart=/opt/vehicle-node/bin/node server.mjs
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
'''
units={'vehicle-benchmark-api':api}
for name,selected in [('vehicle-benchmark-run',ids),('vehicle-benchmark-sonic',['sonic'])]:
 units[name]=f'''[Unit]
Description=Vehicle benchmark evaluator {name}
After=vehicle-benchmark-api.service
Requires=vehicle-benchmark-api.service
[Service]
User=ubuntu
WorkingDirectory=/opt/vehicle-benchmark
Environment=BENCH_BASE=http://127.0.0.1:8788
Environment=BENCH_RELEASE_SHA={sha}
ExecStartPre=/bin/sleep 2
ExecStart=/opt/vehicle-node/bin/node scripts/run-deployment-benchmarks.mjs {' '.join(selected)}
Restart=no
NoNewPrivileges=true
PrivateTmp=true
'''
for name,content in units.items():
 p=ROOT/'.runtime'/f'{name}.service';p.write_text(content);scp(p,'/tmp/'+p.name)
 ssh(f'sudo install -m 644 /tmp/{p.name} /etc/systemd/system/{p.name}')
ssh('sudo systemctl daemon-reload && sudo systemctl restart vehicle-benchmark-api && sudo systemctl start vehicle-benchmark-run vehicle-benchmark-sonic')
(ROOT/'.runtime/benchmark-job.json').write_text(json.dumps({'releaseSha256':sha,'models':ids+['sonic'],'suites':['original31','hard48'],'privateBackendPort':8788},indent=2))
print(json.dumps({'started':True,'models':14,'scoredInputs':14*(31+48),'releaseSha256':sha}))
