"""Idempotent IAM-authenticated AgentCore Gateway + keyless provider Lambda.

Uses the existing deployment account; checkpoints contain resource identifiers,
never AWS keys. Run again after changing assistant-providers.mjs.
"""
import json, os, pathlib, subprocess, tempfile, time, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime/assistant-tools.json'
cloud = json.loads((ROOT / '.runtime/cloud-deployment.json').read_text())
state = json.loads(STATE.read_text()) if STATE.exists() else {}
profile = os.environ.get('AWS_PROFILE', cloud['profile'])
region = os.environ.get('TOOLS_REGION', 'ap-northeast-1')
name = 'vehicle-voice-tools'
def save():
    STATE.write_text(json.dumps(state, indent=2)); os.chmod(STATE, 0o600)
def aws(service, operation, data=None, extra=None):
    cmd = ['aws', '--profile', profile, '--region', region, service, operation]
    if data is not None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=ROOT/'.runtime') as f:
            json.dump(data, f); f.flush()
            p = subprocess.run(cmd+['--cli-input-json', 'file://'+f.name, '--output', 'json']+(extra or []), capture_output=True, text=True)
    else:
        p = subprocess.run(cmd+['--output', 'json']+(extra or []), capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr)
    return json.loads(p.stdout) if p.stdout.strip() else {}
account = aws('sts', 'get-caller-identity')['Account']
tags = {'Project': 'vehicle-voice-lab', 'ManagedBy': 'Codex'}
def role(suffix, service):
    role_name = name+'-'+suffix
    try: return aws('iam', 'get-role', {'RoleName': role_name})['Role']['Arn']
    except RuntimeError as e:
        if 'NoSuchEntity' not in str(e): raise
    return aws('iam', 'create-role', {'RoleName': role_name, 'AssumeRolePolicyDocument': json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':service},'Action':'sts:AssumeRole','Condition':{'StringEquals':{'aws:SourceAccount':account}}}]})})['Role']['Arn']
lambda_role = role('lambda', 'lambda.amazonaws.com')
lambda_arn = f'arn:aws:lambda:{region}:{account}:function:{name}'
aws('iam','put-role-policy',{'RoleName':name+'-lambda','PolicyName':'OwnLogs','PolicyDocument':json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['logs:CreateLogGroup','logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{name}:*'}]})})
bundle = ROOT/'.runtime/assistant-tools.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(ROOT/'assistant-providers.mjs','assistant-providers.mjs')
try:
    aws('lambda','get-function',{'FunctionName':name})
    aws('lambda','update-function-code',extra=['--function-name',name,'--zip-file','fileb://'+str(bundle)])
except RuntimeError as e:
    if 'ResourceNotFoundException' not in str(e): raise
    for attempt in range(5):
        try:
            aws('lambda','create-function',{'FunctionName':name,'Runtime':'nodejs22.x','Role':lambda_role,'Handler':'assistant-providers.handler','Timeout':12,'MemorySize':256,'Architectures':['arm64'],'Tags':tags},extra=['--zip-file','fileb://'+str(bundle)])
            break
        except RuntimeError as retry:
            if 'cannot be assumed' not in str(retry) or attempt==4: raise
            time.sleep(5)
gateway_role = role('gateway','bedrock-agentcore.amazonaws.com')
policy={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'lambda:InvokeFunction','Resource':lambda_arn},{'Effect':'Allow','Action':'bedrock-agentcore:InvokeWebSearch','Resource':f'arn:aws:bedrock-agentcore:{region}:aws:tool/web-search.v1'}]}
aws('iam','put-role-policy',{'RoleName':name+'-gateway','PolicyName':'OwnToolsOnly','PolicyDocument':json.dumps(policy)})
state.update(profile=profile,region=region,lambdaArn=lambda_arn);save()
if not state.get('gatewayId'):
    existing=aws('bedrock-agentcore-control','list-gateways',{'maxResults':100}).get('items',[])
    match=next((x for x in existing if x['name']==name),None)
    if match:
        g=aws('bedrock-agentcore-control','get-gateway',{'gatewayIdentifier':match['gatewayId']})
    else:
        g=aws('bedrock-agentcore-control','create-gateway',{'name':name,'description':'Keyless vehicle demo information tools; vehicle controls stay local','roleArn':gateway_role,'protocolType':'MCP','authorizerType':'AWS_IAM','tags':tags})
    state.update(gatewayId=g['gatewayId'],gatewayArn=g['gatewayArn'],gatewayUrl=g['gatewayUrl']);save()
g=aws('bedrock-agentcore-control','get-gateway',{'gatewayIdentifier':state['gatewayId']})
if g['status']!='READY':
    print(json.dumps({'phase':'gateway','status':g['status']}));raise SystemExit()
targets=aws('bedrock-agentcore-control','list-gateway-targets',{'gatewayIdentifier':state['gatewayId'],'maxResults':100}).get('items',[])
schema=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import{lookupSchema}from'./assistant-providers.mjs';console.log(JSON.stringify(lookupSchema))"],cwd=ROOT,text=True))
def gateway_schema(value):
    allowed={'type','properties','required','items','description'}
    result={k:v for k,v in value.items() if k in allowed}
    if 'properties' in result: result['properties']={k:gateway_schema(v) for k,v in result['properties'].items()}
    if 'items' in result: result['items']=gateway_schema(result['items'])
    return result
schema=gateway_schema(schema)  # Gateway's Lambda schema subset; runtime validates bounds.
for target_name,config in [
 ('providers',{'lambda':{'lambdaArn':lambda_arn,'toolSchema':{'inlinePayload':[{'name':'lookup','description':'Keyless weather, radio, Korean holidays, exchange rates, sunset, Wikipedia, OSM routes and nearby places. No vehicle writes.','inputSchema':schema}]}}}),
 ('search',{'connector':{'source':{'connectorId':'web-search','version':'1.2.0'},'configurations':[{'name':'WebSearch','parameterValues':{}}]}})
]:
    if not any(t['name']==target_name for t in targets):
        t=aws('bedrock-agentcore-control','create-gateway-target',{'gatewayIdentifier':state['gatewayId'],'name':target_name,'targetConfiguration':{'mcp':config},'credentialProviderConfigurations':[{'credentialProviderType':'GATEWAY_IAM_ROLE'}]})
        state[target_name+'TargetId']=t['targetId'];save()
aws('iam','put-role-policy',{'RoleName':cloud['roleName'],'PolicyName':'VehicleAssistantGateway','PolicyDocument':json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'bedrock-agentcore:InvokeGateway','Resource':state['gatewayArn']}]})})
state['ready']=True;save()
print(json.dumps({'ready':True,'region':region,'credentials':'IAM instance role','targets':['providers','search']}))
