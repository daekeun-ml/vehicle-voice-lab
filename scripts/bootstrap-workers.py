"""Install reference workers on instances already created by infra/provision*.py."""
import argparse,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--worker',choices=['core','speech','all'],default='core');p.add_argument('--with-minicpm',action='store_true');args=p.parse_args()
for name in (['core','speech'] if args.worker=='all' else [args.worker]):
 statepath=ROOT/('.runtime/aws.json' if name=='core' else '.runtime/speech-aws.json');state=json.loads(statepath.read_text())
 result=subprocess.run(['aws','--profile',state['profile'],'--region',state['region'],'ec2','describe-instances','--instance-ids',state['instanceId'],'--output','json'],check=True,capture_output=True,text=True)
 instance=json.loads(result.stdout)['Reservations'][0]['Instances'][0]
 if instance['State']['Name']!='running':raise SystemExit(name+' must be running; use scripts/gpu.py start first')
 ip=instance['PublicIpAddress'];state['publicIp']=ip
 options=['-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(ROOT/'.runtime/known_hosts'),'-i',str(ROOT/'.runtime/vehicle-key')]
 directory='/opt/vehicle-voice' if name=='core' else '/opt/vehicle-speech'
 def ssh(command):subprocess.run(['ssh',*options,'ubuntu@'+ip,command],check=True)
 ssh('sudo mkdir -p '+directory+' && sudo chown ubuntu:ubuntu '+directory)
 files=[p for p in (ROOT/'runtime').iterdir() if p.suffix in ('.py','.sh','.json','.txt')]
 if name=='core':files.append(ROOT/'public/reference-neutral.wav')
 subprocess.run(['scp',*options,*map(str,files),'ubuntu@'+ip+':'+directory+'/'],check=True)
 if name=='core':
  ssh('bash '+directory+'/bootstrap.sh && bash '+directory+'/bootstrap_whisper.sh')
  state['whisperEnabled']=True
  if args.with_minicpm:ssh('bash '+directory+'/bootstrap_minicpm.sh')
 else:ssh('bash '+directory+'/bootstrap_speech.sh')
 statepath.write_text(json.dumps(state,indent=2));statepath.chmod(0o600)
 print(name+' worker setup complete; check service health after model loading.')
