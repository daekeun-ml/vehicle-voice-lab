"""One speech model process at a time; keeps incompatible runtimes isolated."""
import asyncio,json,os,pathlib,time
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI,HTTPException,UploadFile,Form,Request
from fastapi.responses import JSONResponse
ROOT=pathlib.Path(__file__).parent
MODELS={'qwen3-omni':'omni-env','step-audio2-mini':'legacy-env','mimo-audio':'legacy-env','moshi':'moshi-env'}
ASR_MODELS={'qwen3-asr-06b':9116,'qwen3-asr-17b':9117}
asr_queues={model:asyncio.Lock() for model in ASR_MODELS}
asr_pending={model:0 for model in ASR_MODELS}
process=None;loaded=None;loading=None;error=None;gate=asyncio.Lock();log=None
async def stop():
 global process,loaded,log
 if process and process.returncode is None:
  process.terminate()
  try:await asyncio.wait_for(process.wait(),15)
  except asyncio.TimeoutError:process.kill();await process.wait()
 process=None;loaded=None
 if log:log.close();log=None
@asynccontextmanager
async def lifespan(app):
 yield
 await stop()
app=FastAPI(lifespan=lifespan)
async def ensure(model_id):
 global process,loaded,loading,error,log
 if model_id not in MODELS:raise HTTPException(400,'Unknown audio model')
 if loaded==model_id and process and process.returncode is None:return 0
 await stop();loading=model_id;error=None;start=time.perf_counter()
 log=open(ROOT/'worker.log','a')
 env_dir=MODELS[model_id]
 module='speech_worker:app'
 process=await asyncio.create_subprocess_exec(str(ROOT/env_dir/'bin/python'),'-m','uvicorn',module,'--host','127.0.0.1','--port','9114',cwd=ROOT,env={**os.environ,'SPEECH_MODEL_ID':model_id,'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},stdout=log,stderr=log)
 try:
  async with httpx.AsyncClient() as client:
   # First Omni NF4 conversion plus durable cache serialization exceeds ten minutes.
   # This readiness budget is separate from per-utterance inference timing.
   for _ in range(1800 if model_id=='qwen3-omni' else 600):
    if process.returncode is not None:raise RuntimeError('음성 모델 프로세스가 종료됐어요. 설치 로그를 확인해 주세요.')
    try:
     h=(await client.get('http://127.0.0.1:9114/health',timeout=2)).json()
     if h.get('error'):raise RuntimeError(h['error'])
     if h.get('ready'):loaded=model_id;return round((time.perf_counter()-start)*1000)
    except (httpx.HTTPError,ValueError):pass
    await asyncio.sleep(1)
  raise RuntimeError('음성 모델 준비 시간이 초과됐어요.')
 except Exception as e:error=str(e);await stop();raise HTTPException(503,error)
 finally:loading=None
@app.get('/health')
async def health():
 async def asr_health(model_id,port):
  try:
   async with httpx.AsyncClient() as client:
    result=(await client.get(f'http://127.0.0.1:{port}/health',timeout=2)).json()
  except (httpx.HTTPError,ValueError):result={'ready':False,'error':'STT worker unavailable'}
  return model_id,{**result,'pendingRequests':asr_pending[model_id]}
 workers=dict(await asyncio.gather(*(asr_health(mid,port) for mid,port in ASR_MODELS.items())))
 h={'ready':True,'loaded':loaded,'loading':loading,'error':error,'available':list(MODELS),
    'asrAvailable':[mid for mid,w in workers.items() if w.get('ready')],
    'asrWorkers':workers,'independentAsr':True,'speechBusy':gate.locked(),'swapModels':True}
 if loaded:
  try:
   async with httpx.AsyncClient() as client:h['worker']=(await client.get('http://127.0.0.1:9114/health',timeout=2)).json()
  except httpx.HTTPError:h['ready']=False
 return h
@app.post('/select')
async def select(body:dict):
 if body.get('modelId') in ASR_MODELS:
  h=await health()
  if body['modelId'] not in h['asrAvailable']:raise HTTPException(503,'선택한 STT 워커를 준비 중입니다.')
  return {'modelId':body['modelId'],'loadMs':0,'independentAsr':True}
 if gate.locked():raise HTTPException(429,'다른 음성 모델 요청을 처리 중이에요.')
 async with gate:return {'modelId':body.get('modelId'),'loadMs':await ensure(body.get('modelId'))}
@app.post('/{operation}')
async def run(operation:str,request:Request,file:UploadFile,model_id:str=Form(...),messages:str=Form('[]'),language:str=Form('ko'),generation_profile:str=Form('deterministic')):
 if operation not in ('plan-audio','s2s','asr'):raise HTTPException(404)
 if (operation=='asr') != (model_id in ASR_MODELS):raise HTTPException(400,'Model does not support this operation')
 if model_id=='moshi' and operation=='plan-audio':raise HTTPException(400,'Moshi는 차량 JSON 도구를 지원하지 않는 음성 비교 모델입니다.')
 raw=await file.read(2_000_001)
 if len(raw)>2_000_000:raise HTTPException(413,'Audio too large')
 if operation=='asr':
  if asr_pending[model_id]>=4:raise HTTPException(503,'STT 요청 대기열이 가득 찼습니다. 잠시 후 다시 시도해 주세요.')
  asr_pending[model_id]+=1
  queued=time.perf_counter()
  try:
   async with asr_queues[model_id]:
    if await request.is_disconnected():raise HTTPException(499,'STT request canceled')
    queue_ms=round((time.perf_counter()-queued)*1000)
    try:
     async with httpx.AsyncClient(timeout=120) as client:
      r=await client.post(f'http://127.0.0.1:{ASR_MODELS[model_id]}/asr',
                         files={'file':('speech.wav',raw,'audio/wav')})
    except httpx.HTTPError:raise HTTPException(504,'STT 워커 연결 또는 응답 시간을 확인해 주세요.')
    try:d=r.json()
    except ValueError:d={'detail':'STT response format error'}
    return JSONResponse({**d,'loadMs':0,'queueMs':queue_ms,'independentAsr':True},status_code=r.status_code)
  finally:asr_pending[model_id]-=1
 if gate.locked():raise HTTPException(429,'다른 음성 모델 요청을 처리 중이에요.')
 async with gate:
  load_ms=await ensure(model_id)
  try:
   async with httpx.AsyncClient(timeout=90) as client:
    r=await client.post('http://127.0.0.1:9114/'+operation,files={'file':('speech.wav',raw,'audio/wav')},data={'messages':messages,'language':language,'generation_profile':generation_profile})
  except httpx.HTTPError:
   await stop()
   raise HTTPException(504,'음성 모델 응답 시간이 초과되거나 연결이 끊겼어요. 모델을 다시 준비한 뒤 재시도해 주세요.')
  try:d=r.json()
  except ValueError:d={'detail':'음성 모델 응답 형식을 확인해 주세요.'}
  d['loadMs']=load_ms
  return JSONResponse(d,status_code=r.status_code)
