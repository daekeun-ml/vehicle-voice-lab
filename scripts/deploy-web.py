"""Upload an allowlisted app bundle and instance-role config, never local credentials."""
import pathlib,json,subprocess,tarfile,os
ROOT=pathlib.Path(__file__).resolve().parents[1];state=json.loads((ROOT/'.runtime/cloud-deployment.json').read_text());core=json.loads((ROOT/'.runtime/aws.json').read_text());speech=json.loads((ROOT/'.runtime/speech-aws.json').read_text())
def ssh(ip,command):return subprocess.run(['ssh','-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key'),'ubuntu@'+ip,command],check=True)
def scp(ip,source,target):return subprocess.run(['scp','-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key'),str(source),'ubuntu@'+ip+':'+target],check=True)
bundle=ROOT/'.runtime/web-release.tar.gz'
with tarfile.open(bundle,'w:gz') as tar:
 for p in list(ROOT.glob('*.mjs'))+[ROOT/n for n in ['package.json','package-lock.json','model-catalog.json','runtime/bootstrap_web.sh','research/vehicle-benchmark-summary.json','research/vehicle-model-comparison.csv']]+list((ROOT/'public').rglob('*'))+list((ROOT/'output/vehicle-benchmark').glob('*-reply.wav')):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(ROOT)))
public=state.get('url','https://pending.invalid')
env={'PORT':'8787','BIND_HOST':'0.0.0.0','PUBLIC_ORIGIN':public,'ORIGIN_HOST':state['originPrivateDns'],'ORIGIN_VERIFY_SECRET':state['originSecret'],'AWS_CREDENTIAL_MODE':'instance','AWS_REGION':state['region'],'SONIC_REGION':os.environ.get('SONIC_REGION','ap-northeast-1'),'SONIC_MODEL':os.environ.get('SONIC_MODEL','amazon.nova-2-5-sonic'),'CORE_URL':'http://127.0.0.1:9101','TTS_URL':'http://127.0.0.1:9102','MINICPM_URL':'http://127.0.0.1:9103','WHISPER_URL':'http://127.0.0.1:9105','SPEECH_URL':'http://'+state['speechPrivateIp']+':9204','NODE_ENV':'production'}
envfile=ROOT/'.runtime/web.env';envfile.write_text('\n'.join(k+'='+v for k,v in env.items())+'\n');os.chmod(envfile,0o600)
ssh(core['publicIp'],'sudo mkdir -p /opt/vehicle-web && sudo chown ubuntu:ubuntu /opt/vehicle-web')
scp(core['publicIp'],bundle,'/tmp/vehicle-web-release.tar.gz');scp(core['publicIp'],envfile,'/tmp/vehicle-web.env')
ssh(core['publicIp'],'tar -xzf /tmp/vehicle-web-release.tar.gz -C /opt/vehicle-web && sudo install -m 600 -o root -g root /tmp/vehicle-web.env /etc/vehicle-web.env && rm /tmp/vehicle-web.env && bash /opt/vehicle-web/runtime/bootstrap_web.sh && sudo systemctl restart vehicle-web')
proxy=f'''[Unit]
Description=Private vehicle speech ingress for own backend
[Socket]
ListenStream={state['speechPrivateIp']}:9204
NoDelay=true
[Install]
WantedBy=sockets.target
'''
service='''[Unit]
Description=Private vehicle speech socket proxy
After=vehicle-speech.service
[Service]
User=nobody
ExecStart=/lib/systemd/systemd-socket-proxyd 127.0.0.1:9104
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
'''
for name,content in [('vehicle-speech-private.socket',proxy),('vehicle-speech-private.service',service)]:
 p=ROOT/'.runtime'/name;p.write_text(content);scp(speech['publicIp'],p,'/tmp/'+name)
ssh(speech['publicIp'],'sudo install -m 644 /tmp/vehicle-speech-private.socket /tmp/vehicle-speech-private.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now vehicle-speech-private.socket')
print(json.dumps({'uploaded':True,'publicOrigin':public,'credentials':'EC2 instance role; no developer keys uploaded'}))
