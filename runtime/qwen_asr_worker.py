"""Pinned Qwen3-ASR adapter, isolated and swapped by speech_manager."""
import io, os, threading, time
from contextlib import asynccontextmanager
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException, UploadFile

SPECS = {
    "qwen3-asr-06b": ("Qwen/Qwen3-ASR-0.6B", "5eb144179a02acc5e5ba31e748d22b0cf3e303b0"),
    "qwen3-asr-17b": ("Qwen/Qwen3-ASR-1.7B", "7278e1e70fe206f11671096ffdd38061171dd6e5"),
}
KIND = os.environ["SPEECH_MODEL_ID"]
REPO, REV = SPECS[KIND]
model = None
lock = threading.Lock()
status = dict(ready=False, modelId=KIND, model=REPO, revision=REV, error=None,
              precision="bfloat16", language="Korean", backend="transformers")

def load():
    global model
    try:
        from huggingface_hub import snapshot_download
        from qwen_asr import Qwen3ASRModel
        path = snapshot_download(REPO, revision=REV)
        model = Qwen3ASRModel.from_pretrained(
            path, dtype=torch.bfloat16, device_map="cuda:0",
            attn_implementation="sdpa", max_inference_batch_size=1, max_new_tokens=256)
        status["ready"] = True
    except Exception as exc:
        import traceback
        traceback.print_exc()
        status["error"] = str(exc)

@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=load, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return status

@app.post("/asr")
def asr(file: UploadFile):
    if not status["ready"]:
        raise HTTPException(503, status["error"] or "ASR loading")
    raw = file.file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(413, "Audio too large")
    try:
        samples, rate = sf.read(io.BytesIO(raw), dtype="float32")
    except Exception:
        raise HTTPException(400, "Invalid audio")
    if rate != 16000 or samples.ndim != 1 or not 0 < len(samples) <= rate * 30 or not np.isfinite(samples).all():
        raise HTTPException(400, "Finite 16kHz mono WAV, max 30 seconds")
    with lock, torch.inference_mode():
        torch.cuda.synchronize()
        start = time.perf_counter()
        result = model.transcribe(audio=(samples, rate), language="Korean")[0]
        torch.cuda.synchronize()
        elapsed = round((time.perf_counter() - start) * 1000)
    return dict(text=result.text.strip(), elapsedMs=elapsed, model=REPO, revision=REV,
                language=result.language, precision="bfloat16")
