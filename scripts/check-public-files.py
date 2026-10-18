"""Check the Git index for private artifacts and common credential formats.
Reports paths and rule names only; never prints matching secrets.
"""
import pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
rules={
 'private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'AWS access key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'GitHub token':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
 'Hugging Face token':r'\bhf_[A-Za-z0-9]{30,}\b',
 'AWS account ARN':r'arn:aws:[^\s\"\']*:[0-9]{12}:',
 'developer absolute path':r'/Users/[A-Za-z0-9_.-]+/',
}
problems=[];checked=0
for name in filter(None,paths):
 if name.startswith(('.runtime/','node_modules/','output/')) or name in ('.env',) or pathlib.Path(name).suffix in ('.pem','.key','.p12','.pfx'):problems.append((name,'private artifact'));continue
 raw=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
 if b'\0'in raw:continue
 try:text=raw.decode('utf8')
 except UnicodeDecodeError:continue
 checked+=1
 for label,pattern in rules.items():
  if re.search(pattern,text):problems.append((name,label))
for name,label in problems:print(name+': '+label)
print(f'Checked {checked} staged text files; {len(problems)} findings.')
sys.exit(bool(problems))
