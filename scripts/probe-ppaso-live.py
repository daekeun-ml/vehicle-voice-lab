"""Same eight TTS phrases, live Ppaso synthesis and Whisper pronunciation proxy."""
import ast,base64,hashlib,io,json,os,re,subprocess,tempfile,time,unicodedata,urllib.request,urllib.error,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=os.environ.get('PPASO_PROBE_URL','https://d2ub6bbyf1c3sv.cloudfront.net')
OUT=ROOT/'research/tts-comparison';(OUT/'ppaso').mkdir(exist_ok=True)
# Reuse the frozen numeric normalization used by the earlier three-model diagnostic.
tree=ast.parse((ROOT/'scripts/tts-comparison-asr.py').read_text())
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['words','normalize','errors'] or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NUMBER_FORMS' for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),'frozen-tts-normalization','exec'))
def request(path,body=None,sid=None,method=None):
 headers={'Content-Type':'application/json'}
 if sid:headers['X-Session-Id']=sid
 with urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method),timeout=180) as response:return json.load(response)
s=request('/api/session',{})
report={'model':'ppaso','repo':'akamotaco/ppaso-tts-v1','revision':'53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9','backend':'onnxruntime CPU; two intra-op threads per session','textNormalization':'ppaso-numeric-v1: preserve decimal fractions and minus signs; development-set fix','humanListeningCompleted':False,'appIntegration':True,'scope':'8 fixed phrases; single synthesis each; Whisper proxy, not MOS','rows':[]}
try:
 for c in json.loads((OUT/'cases.json').read_text())['cases']:
  r=request('/api/tts/preview',{'ttsProvider':'ppaso','text':c['text']},s['id'])
  assert r['model']==report['repo'] and r['revision']==report['revision']
  data=base64.b64decode(r['audio']);path=OUT/'ppaso'/(c['id']+'.wav');path.write_bytes(data)
  with wave.open(io.BytesIO(data)) as w:
   assert w.getframerate()==22050 and w.getnchannels()==1
   duration=w.getnframes()/w.getframerate();assert duration>.1
  with tempfile.TemporaryDirectory() as folder:
   converted=Path(folder)/'16k.wav'
   subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(path),'-ar','16000','-ac','1',str(converted)],check=True)
   transcription=request('/api/asr/transcribe',{'asrId':'whisper','audio':base64.b64encode(converted.read_bytes()).decode()},s['id'])
  a,b=normalize(c['text']),normalize(transcription['text'])
  row={**c,'file':str(path.relative_to(ROOT)),'sampleRate':22050,'durationSeconds':duration,'synthesisMs':r['inferenceMs'],'realTimeFactor':r['inferenceMs']/1000/duration,'transcript':transcription['text'],'normalizedExact':a==b,'characterErrors':errors(a,b),'referenceCharacters':len(a),'numberSequenceMatches':re.findall(r'\d+(?:\.\d+)?',words(c['text']))==re.findall(r'\d+(?:\.\d+)?',words(transcription['text'])),'sha256':hashlib.sha256(data).hexdigest()}
  report['rows'].append(row);(OUT/'ppaso.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row,ensure_ascii=False),flush=True)
 exported=request('/api/export',sid=s['id']);assert exported['state']==s['state'] and not exported['turns'];report['vehicleStateUnchanged']=True
 try:request('/api/tts/preview',{'ttsProvider':'kokoro','text':'안녕하세요.'},s['id']);raise AssertionError('Removed Kokoro accepted')
 except urllib.error.HTTPError as e:assert e.code==400
 report['kokoroRejected']=True
finally:request('/api/session',sid=s['id'],method='DELETE')
(OUT/'ppaso.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
