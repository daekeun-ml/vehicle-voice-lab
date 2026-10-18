"""One-command launcher for this local test environment."""
import pathlib,subprocess,json,time,sys,os,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];os.chdir(ROOT)
existing_server=False
try:
 health=json.load(urllib.request.urlopen('http://localhost:8787/api/health',timeout=3));existing_server=True
 if health['ready'] and health.get('asrWorkers',{}).get('whisper',{}).get('ready') and (not (ROOT/'.runtime/speech-aws.json').exists() or health.get('researchWorkers',{}).get('speech',{}).get('ready')):
  subprocess.run(['open','-a','Google Chrome','http://localhost:8787']);print('테스트 화면이 이미 실행 중입니다.');raise SystemExit()
except (OSError,TimeoutError):pass
status=json.loads(subprocess.check_output([sys.executable,'scripts/gpu.py','status'],text=True))
if status['state']=='stopped' or status.get('speech',{}).get('state')=='stopped':subprocess.run([sys.executable,'scripts/gpu.py','start'],check=True)
for attempt in range(90):
 status=json.loads(subprocess.check_output([sys.executable,'scripts/gpu.py','status'],text=True))
 if status['state']=='running' and status.get('speech',{}).get('state','running')=='running':break
 time.sleep(2)
else:raise SystemExit('GPU가 실행되지 않았습니다. scripts/gpu.py status로 확인해 주세요.')
# EC2 running precedes SSH readiness after a cold boot.
for worker in [status]+([status['speech']] if status.get('speech') else []):
 ssh_probe=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key'),'ubuntu@'+worker['publicIp'],'true']
 for attempt in range(60):
  if subprocess.run(ssh_probe,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(2)
 else:raise SystemExit('GPU의 SSH 연결이 준비되지 않았습니다. 네트워크와 보안 그룹을 확인해 주세요.')
log=open(ROOT/'.runtime/local.log','a')
tunnels={}
for worker,port in [('core',19101),('speech',19104)]:
 if worker=='speech' and not (ROOT/'.runtime/speech-aws.json').exists():continue
 import socket
 with socket.socket() as probe: listening=probe.connect_ex(('127.0.0.1',port))==0
 if not listening:tunnels[worker]=subprocess.Popen([sys.executable,'scripts/gpu.py','tunnel','--worker',worker],stdout=log,stderr=log,start_new_session=True)

# Existing core tunnels created before Whisper may lack its forward.
if json.loads((ROOT/'.runtime/aws.json').read_text()).get('whisperEnabled'):
 import socket
 with socket.socket() as probe: whisper_listening=probe.connect_ex(('127.0.0.1',19105))==0
 if not whisper_listening:
  whisper_tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key'),'-L','127.0.0.1:19105:127.0.0.1:9105','ubuntu@'+status['publicIp']],stdout=log,stderr=log,start_new_session=True)
 else: whisper_tunnel=None
else: whisper_tunnel=None

server=None if existing_server else subprocess.Popen(['node','server.mjs'],stdout=log,stderr=log,start_new_session=True)
process_path=ROOT/'.runtime/local-processes.json'
previous=json.loads(process_path.read_text()) if process_path.exists() else {}
process_path.write_text(json.dumps({**previous,'tunnelPid':tunnels['core'].pid if 'core' in tunnels else previous.get('tunnelPid'),'speechTunnelPid':tunnels['speech'].pid if 'speech' in tunnels else previous.get('speechTunnelPid'),'serverPid':server.pid if server else previous.get('serverPid'),'whisperTunnelPid':whisper_tunnel.pid if whisper_tunnel else previous.get('whisperTunnelPid')}))
for attempt in range(30):
 try:urllib.request.urlopen('http://localhost:8787/api/health',timeout=3);break
 except OSError:time.sleep(1)
subprocess.run(['open','-a','Google Chrome','http://localhost:8787']);print('테스트 화면을 열었습니다. GPU 모델 로딩이 끝나면 마이크를 켜세요.')
