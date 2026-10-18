import json,subprocess,pathlib,urllib.request,time,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
REGION=os.environ.get('AWS_REGION','ap-northeast-2'); PROFILE=os.environ.get('AWS_PROFILE','default')
(ROOT/'.runtime').mkdir(mode=0o700,exist_ok=True)
def aws(*args):
 p=subprocess.run(['aws','--profile',PROFILE,'--region',REGION,*args,'--output','json'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout) if p.stdout.strip() else {}
def invoke(service,op,data):
 f=ROOT/'.runtime'/'request.json';f.write_text(json.dumps(data))
 return aws(service,op,'--cli-input-json','file://'+str(f))
statefile=ROOT/'.runtime'/'aws.json'
if statefile.exists():
 print(statefile.read_text());raise SystemExit()
required=['AWS_VPC_ID','AWS_SUBNET_ID','AWS_AMI_ID']
missing=[k for k in required if not os.environ.get(k)]
if missing:raise SystemExit('Set deployment environment variables: '+', '.join(missing))
ip=urllib.request.urlopen('https://checkip.amazonaws.com').read().decode().strip()
name='vehicle-voice-lab-'+str(int(time.time()))
sg=invoke('ec2','create-security-group',{'GroupName':name,'Description':'Vehicle voice lab: SSH from developer IP only','VpcId':os.environ['AWS_VPC_ID'],'TagSpecifications':[{'ResourceType':'security-group','Tags':[{'Key':'Project','Value':'vehicle-voice-lab'}]}]})['GroupId']
invoke('ec2','authorize-security-group-ingress',{'GroupId':sg,'IpPermissions':[{'IpProtocol':'tcp','FromPort':22,'ToPort':22,'IpRanges':[{'CidrIp':ip+'/32','Description':'Developer SSH tunnel'}]}]})
keyname=name
invoke('ec2','import-key-pair',{'KeyName':keyname,'PublicKeyMaterial':__import__('base64').b64encode((ROOT/'.runtime'/'vehicle-key.pub').read_bytes()).decode()})
userdata='''#!/bin/bash
set -eux
apt-get update
apt-get install -y python3-venv ffmpeg libsndfile1
mkdir -p /opt/vehicle-voice
chown ubuntu:ubuntu /opt/vehicle-voice
cat > /etc/systemd/system/vehicle-auto-stop.service <<'UNIT'
[Unit]
Description=Stop vehicle test GPU after four hours
[Service]
Type=oneshot
ExecStart=/usr/sbin/shutdown -h now
UNIT
cat > /etc/systemd/system/vehicle-auto-stop.timer <<'UNIT'
[Unit]
Description=Vehicle test GPU four-hour limit
[Timer]
OnBootSec=4h
Unit=vehicle-auto-stop.service
[Install]
WantedBy=timers.target
UNIT
systemctl enable --now vehicle-auto-stop.timer
'''
request={'ImageId':os.environ['AWS_AMI_ID'],'InstanceType':'g6e.2xlarge','MinCount':1,'MaxCount':1,'KeyName':keyname,'NetworkInterfaces':[{'DeviceIndex':0,'SubnetId':os.environ['AWS_SUBNET_ID'],'Groups':[sg],'AssociatePublicIpAddress':True}],'BlockDeviceMappings':[{'DeviceName':'/dev/sda1','Ebs':{'VolumeSize':150,'VolumeType':'gp3','DeleteOnTermination':True,'Encrypted':True}}],'MetadataOptions':{'HttpTokens':'required','HttpEndpoint':'enabled'},'InstanceInitiatedShutdownBehavior':'stop','UserData':__import__('base64').b64encode(userdata.encode()).decode(),'TagSpecifications':[{'ResourceType':'instance','Tags':[{'Key':'Name','Value':'vehicle-voice-lab'},{'Key':'Project','Value':'vehicle-voice-lab'},{'Key':'ManagedBy','Value':'Codex'}]},{'ResourceType':'volume','Tags':[{'Key':'Project','Value':'vehicle-voice-lab'}]}]}
try: instance=invoke('ec2','run-instances',request)['Instances'][0]
except Exception:
 aws('ec2','delete-key-pair','--key-name',keyname);aws('ec2','delete-security-group','--group-id',sg);raise
state={'profile':PROFILE,'region':REGION,'instanceId':instance['InstanceId'],'securityGroupId':sg,'keyName':keyname,'instanceType':request['InstanceType'],'createdAt':time.time(),'autoStopHours':4,'autoStopEnabled':True,'subnetId':os.environ['AWS_SUBNET_ID'],'imageId':os.environ['AWS_AMI_ID']}
statefile.write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
