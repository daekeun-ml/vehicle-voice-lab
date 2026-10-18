"""Provision one swappable speech-model GPU, isolated by the existing SSH SG."""
import json,subprocess,pathlib,time,base64,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
statefile=ROOT/'.runtime/speech-aws.json'
base=json.loads((ROOT/'.runtime/aws.json').read_text())
# Reuse the core worker region, subnet, and DLAMI, not a developer account's IDs.
def aws(*args):
 p=subprocess.run(['aws','--profile',base['profile'],'--region',base['region'],*args,'--output','json'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout) if p.stdout.strip() else {}
if statefile.exists():print(statefile.read_text());raise SystemExit()
core=aws('ec2','describe-instances','--instance-ids',base['instanceId'])['Reservations'][0]['Instances'][0]
userdata='''#!/bin/bash
set -eux
mkdir -p /opt/vehicle-speech
chown ubuntu:ubuntu /opt/vehicle-speech
cat > /etc/systemd/system/vehicle-auto-stop.service <<'UNIT'
[Unit]
Description=Stop vehicle speech test GPU after four hours
[Service]
Type=oneshot
ExecStart=/usr/sbin/shutdown -h now
UNIT
cat > /etc/systemd/system/vehicle-auto-stop.timer <<'UNIT'
[Unit]
Description=Vehicle speech GPU four-hour limit
[Timer]
OnBootSec=4h
Unit=vehicle-auto-stop.service
[Install]
WantedBy=timers.target
UNIT
systemctl enable --now vehicle-auto-stop.timer
'''
request={'ImageId':os.environ.get('AWS_AMI_ID',core['ImageId']),'InstanceType':'g6e.2xlarge','MinCount':1,'MaxCount':1,'KeyName':base['keyName'],'NetworkInterfaces':[{'DeviceIndex':0,'SubnetId':core['SubnetId'],'Groups':[base['securityGroupId']],'AssociatePublicIpAddress':True}],'BlockDeviceMappings':[{'DeviceName':'/dev/sda1','Ebs':{'VolumeSize':250,'VolumeType':'gp3','DeleteOnTermination':True,'Encrypted':True}}],'MetadataOptions':{'HttpTokens':'required','HttpEndpoint':'enabled'},'InstanceInitiatedShutdownBehavior':'stop','UserData':base64.b64encode(userdata.encode()).decode(),'TagSpecifications':[{'ResourceType':'instance','Tags':[{'Key':'Name','Value':'vehicle-speech-alternatives'},{'Key':'Project','Value':'vehicle-voice-lab'},{'Key':'ManagedBy','Value':'Codex'}]},{'ResourceType':'volume','Tags':[{'Key':'Project','Value':'vehicle-voice-lab'}]}]}
f=ROOT/'.runtime/speech-request.json';f.write_text(json.dumps(request))
instance=aws('ec2','run-instances','--cli-input-json','file://'+str(f))['Instances'][0]
state={'profile':base['profile'],'region':base['region'],'instanceId':instance['InstanceId'],'securityGroupId':base['securityGroupId'],'keyName':base['keyName'],'instanceType':request['InstanceType'],'createdAt':time.time(),'autoStopHours':4,'autoStopEnabled':True,'subnetId':core['SubnetId'],'imageId':request['ImageId']}
statefile.write_text(json.dumps(state,indent=2));print(json.dumps(state,indent=2))
