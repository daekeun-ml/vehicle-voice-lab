"""Provision this lab's CloudFront VPC origin; checkpoint every created resource."""
import json,pathlib,subprocess,secrets,os,tempfile,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'.runtime/cloud-deployment.json'
state=json.loads(STATE.read_text()) if STATE.exists() else {'project':'vehicle-voice-lab','name':os.environ.get('DEPLOYMENT_NAME','vehicle-voice-share-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S'))}
def save():STATE.write_text(json.dumps(state,indent=2));os.chmod(STATE,0o600)
def aws(service,operation,**data):
 with tempfile.NamedTemporaryFile(mode='w',suffix='.json',dir=ROOT/'.runtime') as f:
  json.dump(data,f);f.flush();p=subprocess.run(['aws','--profile',state['profile'],'--region',state['region'],service,operation,'--cli-input-json','file://'+f.name,'--output','json'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout) if p.stdout.strip() else {}
def tags():return [{'Key':'Project','Value':state['project']},{'Key':'ManagedBy','Value':'Codex'}]
core=json.loads((ROOT/'.runtime/aws.json').read_text());speech=json.loads((ROOT/'.runtime/speech-aws.json').read_text())
state['profile']=core['profile'];state['region']=core['region']
instances=aws('ec2','describe-instances',InstanceIds=[core['instanceId'],speech['instanceId']])
items={i['InstanceId']:i for r in instances['Reservations'] for i in r['Instances']};a=items[core['instanceId']];b=items[speech['instanceId']]
state.update(coreInstanceId=a['InstanceId'],corePrivateIp=a['PrivateIpAddress'],speechPrivateIp=b['PrivateIpAddress'],vpcId=a['VpcId'],originPrivateDns=a['PrivateDnsName'])
account=aws('sts','get-caller-identity')['Account'];state['account']=account;save()
if 'originSecret' not in state:state['originSecret']=secrets.token_urlsafe(48);save()
if 'webSecurityGroupId' not in state:
 state['webSecurityGroupId']=aws('ec2','create-security-group',GroupName=state['name']+'-web',Description='Vehicle voice CloudFront private web origin',VpcId=a['VpcId'],TagSpecifications=[{'ResourceType':'security-group','Tags':tags()}])['GroupId'];save()
 prefix=aws('ec2','describe-managed-prefix-lists',Filters=[{'Name':'prefix-list-name','Values':['com.amazonaws.global.cloudfront.origin-facing']}])['PrefixLists'][0]['PrefixListId']
 aws('ec2','authorize-security-group-ingress',GroupId=state['webSecurityGroupId'],IpPermissions=[{'IpProtocol':'tcp','FromPort':8787,'ToPort':8787,'PrefixListIds':[{'PrefixListId':prefix,'Description':'CloudFront VPC origin bootstrap'}]}])
groups=[g['GroupId'] for g in a['SecurityGroups']]
if state['webSecurityGroupId'] not in groups:aws('ec2','modify-instance-attribute',InstanceId=a['InstanceId'],Groups=groups+[state['webSecurityGroupId']])
if 'peerSecurityGroupId' not in state:
 state['peerSecurityGroupId']=aws('ec2','create-security-group',GroupName=state['name']+'-speech',Description='Vehicle speech proxy from own web backend only',VpcId=a['VpcId'],TagSpecifications=[{'ResourceType':'security-group','Tags':tags()}])['GroupId'];save()
 aws('ec2','authorize-security-group-ingress',GroupId=state['peerSecurityGroupId'],IpPermissions=[{'IpProtocol':'tcp','FromPort':9204,'ToPort':9204,'UserIdGroupPairs':[{'GroupId':state['webSecurityGroupId'],'Description':'Own backend to speech proxy'}]}])
groups=[g['GroupId'] for g in b['SecurityGroups']]
if state['peerSecurityGroupId'] not in groups:aws('ec2','modify-instance-attribute',InstanceId=b['InstanceId'],Groups=groups+[state['peerSecurityGroupId']])
name=state['name']+'-runtime'
if 'instanceProfileArn' not in state:
 trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ec2.amazonaws.com'},'Action':'sts:AssumeRole'}]}
 try:role=aws('iam','create-role',RoleName=name,AssumeRolePolicyDocument=json.dumps(trust),Description='Vehicle demo Polly and one Sonic model only',Tags=tags())
 except RuntimeError as e:
  if 'EntityAlreadyExists' not in str(e):raise
 policy={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['polly:SynthesizeSpeech'],'Resource':'*','Condition':{'StringEquals':{'aws:RequestedRegion':state['region']}}},{'Effect':'Allow','Action':['bedrock:InvokeModel'],'Resource':'arn:aws:bedrock:'+os.environ.get('SONIC_REGION','ap-northeast-1')+'::foundation-model/'+os.environ.get('SONIC_MODEL','amazon.nova-2-5-sonic')}]}
 aws('iam','put-role-policy',RoleName=name,PolicyName='VehicleVoiceInferenceOnly',PolicyDocument=json.dumps(policy))
 try:profile=aws('iam','create-instance-profile',InstanceProfileName=name,Tags=tags())
 except RuntimeError as e:
  if 'EntityAlreadyExists' not in str(e):raise
  profile=aws('iam','get-instance-profile',InstanceProfileName=name)
 try:aws('iam','add-role-to-instance-profile',InstanceProfileName=name,RoleName=name)
 except RuntimeError as e:
  if 'LimitExceeded' not in str(e):raise
 state['instanceProfileArn']=profile['InstanceProfile']['Arn'];state['roleName']=name;save()
if not a.get('IamInstanceProfile'):
 try:aws('ec2','associate-iam-instance-profile',InstanceId=a['InstanceId'],IamInstanceProfile={'Arn':state['instanceProfileArn']})
 except RuntimeError as e:
  if 'InvalidParameterValue' not in str(e):raise
elif a['IamInstanceProfile']['Arn']!=state['instanceProfileArn']:raise RuntimeError('Unexpected existing role; will not replace it')
if 'vpcOriginId' not in state:
 result=aws('cloudfront','create-vpc-origin',VpcOriginEndpointConfig={'Name':state['name'],'Arn':f"arn:aws:ec2:{state['region']}:{account}:instance/{a['InstanceId']}",'HTTPPort':8787,'HTTPSPort':443,'OriginProtocolPolicy':'http-only','OriginSslProtocols':{'Quantity':1,'Items':['TLSv1.2']}},Tags={'Items':tags()})
 state['vpcOriginId']=result['VpcOrigin']['Id'];save()
origin=aws('cloudfront','get-vpc-origin',Id=state['vpcOriginId'])['VpcOrigin'];state['vpcOriginStatus']=origin['Status'];save()
print(json.dumps({k:state.get(k) for k in ['vpcOriginId','vpcOriginStatus','webSecurityGroupId','corePrivateIp','speechPrivateIp']}))
if origin['Status']!='Deployed':raise SystemExit()
sg=aws('ec2','describe-security-groups',Filters=[{'Name':'vpc-id','Values':[a['VpcId']]},{'Name':'group-name','Values':['CloudFront-VPCOrigins-Service-SG*']}])['SecurityGroups']
if sg and not state.get('serviceGroupRestricted'):
 group=state['webSecurityGroupId'];current=aws('ec2','describe-security-groups',GroupIds=[group])['SecurityGroups'][0]['IpPermissions']
 aws('ec2','authorize-security-group-ingress',GroupId=group,IpPermissions=[{'IpProtocol':'tcp','FromPort':8787,'ToPort':8787,'UserIdGroupPairs':[{'GroupId':sg[0]['GroupId'],'Description':'CloudFront VPC service only'}]}])
 for p in current:
  if p.get('PrefixListIds'):aws('ec2','revoke-security-group-ingress',GroupId=group,IpPermissions=[p])
 state['serviceGroupRestricted']=True;save()
if 'distributionId' not in state:
 policies=aws('cloudfront','list-cache-policies',Type='managed')['CachePolicyList']['Items'];cache={x['CachePolicy']['CachePolicyConfig']['Name']:x['CachePolicy']['Id'] for x in policies}
 policies=aws('cloudfront','list-origin-request-policies',Type='managed')['OriginRequestPolicyList']['Items'];request={x['OriginRequestPolicy']['OriginRequestPolicyConfig']['Name']:x['OriginRequestPolicy']['Id'] for x in policies}
 common={'TargetOriginId':'vehicle-private-web','ViewerProtocolPolicy':'redirect-to-https','TrustedSigners':{'Enabled':False,'Quantity':0},'TrustedKeyGroups':{'Enabled':False,'Quantity':0},'Compress':True}
 config={'CallerReference':state['name'],'Comment':'Vehicle voice shared demo / Seoul L40S / private VPC origin','Enabled':True,'DefaultRootObject':'index.html','Aliases':{'Quantity':0},'Origins':{'Quantity':1,'Items':[{'Id':'vehicle-private-web','DomainName':state['originPrivateDns'],'CustomHeaders':{'Quantity':1,'Items':[{'HeaderName':'X-Vehicle-Origin-Key','HeaderValue':state['originSecret']}]},'VpcOriginConfig':{'VpcOriginId':state['vpcOriginId'],'OriginReadTimeout':60,'OriginKeepaliveTimeout':60},'ConnectionAttempts':3,'ConnectionTimeout':10}]},'DefaultCacheBehavior':{**common,'AllowedMethods':{'Quantity':2,'Items':['GET','HEAD'],'CachedMethods':{'Quantity':2,'Items':['GET','HEAD']}},'CachePolicyId':cache['Managed-CachingOptimized']},'CacheBehaviors':{'Quantity':1,'Items':[{**common,'PathPattern':'/api/*','AllowedMethods':{'Quantity':7,'Items':['GET','HEAD','OPTIONS','PUT','PATCH','POST','DELETE'],'CachedMethods':{'Quantity':2,'Items':['GET','HEAD']}},'CachePolicyId':cache['Managed-CachingDisabled'],'OriginRequestPolicyId':request['Managed-AllViewer']}]},'ViewerCertificate':{'CloudFrontDefaultCertificate':True},'PriceClass':'PriceClass_All','HttpVersion':'http2and3','IsIPV6Enabled':True,'Restrictions':{'GeoRestriction':{'RestrictionType':'none','Quantity':0}}}
 result=aws('cloudfront','create-distribution',DistributionConfig=config)['Distribution'];state['distributionId']=result['Id'];state['domain']=result['DomainName'];state['url']='https://'+result['DomainName'];save()
dist=aws('cloudfront','get-distribution',Id=state['distributionId'])['Distribution'];state['distributionStatus']=dist['Status'];save();print(json.dumps({'url':state['url'],'status':state['distributionStatus']}))
