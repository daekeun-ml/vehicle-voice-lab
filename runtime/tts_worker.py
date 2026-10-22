"""Pinned Qwen 1.7B / Supertonic worker. Bind to loopback; one synthesis at a time."""
import asyncio
import io
import os
import time
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

ENGINE = os.environ.get("TTS_ENGINE", "supertonic")
SPECS = {
    "qwen17": ("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "0c0e3051f131929182e2c023b9537f8b1c68adfe", "Sohee"),
    "supertonic": ("Supertone/supertonic-3", "3cadd1ee6394adea1bd021217a0e650ede09a323", "F1"),
    "ppaso": ("akamotaco/ppaso-tts-v1", "53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9", "single-female"),
}
if ENGINE not in SPECS:
    raise ValueError("Unsupported TTS_ENGINE")
REPO, REVISION, VOICE = SPECS[ENGINE]
status = {"ready": False, "engine": ENGINE, "model": REPO, "revision": REVISION,
          "voice": VOICE, "device": "cuda:0" if ENGINE == "qwen17" else "cpu", "error": None}
model = style = None
queue = asyncio.Lock()
pending = 0


def load():
    global model, style
    try:
        from huggingface_hub import snapshot_download
        folder = os.environ.get("TTS_MODEL_DIR") or snapshot_download(
            REPO, revision=REVISION,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "onnx/*", "voice_styles/*", "runtime/**", "example/ppaso_tts.py", "LICENSE", "README*.md"],
        )
        if ENGINE == "supertonic":
            from supertonic import TTS
            model = TTS(model="supertonic-3", model_dir=folder, auto_download=False,
                        intra_op_num_threads=4, inter_op_num_threads=1)
            style = model.get_voice_style(voice_name=VOICE)
            status["sampleRate"] = model.sample_rate
        elif ENGINE == "ppaso":
            import sys
            import shutil
            import tempfile
            import onnxruntime as ort
            # ORT external-data validation rejects HF cache symlinks across blob directories.
            # Materialize the pinned snapshot; keep the validation enabled.
            materialized = Path(os.environ.get("HF_HOME", "./models"))/"ppaso-materialized"/REVISION
            if not materialized.exists():
                materialized.parent.mkdir(parents=True, exist_ok=True)
                temp = Path(tempfile.mkdtemp(prefix=".ppaso-", dir=materialized.parent))
                shutil.copytree(folder, temp, dirs_exist_ok=True, symlinks=False)
                os.replace(temp, materialized)
            folder = str(materialized)
            sys.path.insert(0, str(Path(folder)/"example"))
            os.environ["PPASO_LEXICON"] = str(Path(folder)/"runtime/dict/korean_mfa.dict")
            import ppaso_tts
            class CpuBackend(ppaso_tts._ONNXBackend):
                def __init__(self, model_dir, device="cpu"):
                    self.sessions = {}
                    for name in ["text_encoder", "variance", "acoustic", "vocoder"]:
                        options = ort.SessionOptions()
                        options.intra_op_num_threads = 2
                        options.inter_op_num_threads = 1
                        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
                        path = ppaso_tts._resolve_model_file(model_dir, name+".onnx", "onnx")
                        self.sessions[name] = ort.InferenceSession(str(path), sess_options=options,
                                                                 providers=["CPUExecutionProvider"])
            ppaso_tts._ONNXBackend = CpuBackend
            model = ppaso_tts.PpasoTTS(folder, backend="onnx", device="cpu")
            status.update(sampleRate=22050, language="ko", backend="onnxruntime-cpu",
                          intraOpThreads=2, singleSpeaker=True)
        else:
            import torch
            from qwen_tts import Qwen3TTSModel
            torch.set_num_threads(4)
            model = Qwen3TTSModel.from_pretrained(
                folder, device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
            status["sampleRate"] = 24000
        status["ready"] = True
    except Exception as error:
        # Full traceback goes to the private service log, not the public health response.
        import traceback
        traceback.print_exc()
        status["error"] = f"{type(error).__name__}: model initialization failed"


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=load, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {**status, "pendingRequests": pending}


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=350)


def synthesize(text):
    start = time.perf_counter()
    if ENGINE == "supertonic":
        wave, _ = model.synthesize(text, voice_style=style, lang="ko", total_steps=8, speed=1.05)
        rate = model.sample_rate
    elif ENGINE == "ppaso":
        from ppaso_text import normalize_ppaso_text
        wave = model.synthesize(normalize_ppaso_text(text))
        rate = 22050
    else:
        waves, rate = model.generate_custom_voice(
            text=text, language="Korean", speaker=VOICE, non_streaming_mode=True, max_new_tokens=1024)
        wave = waves[0]
    samples = np.asarray(wave, dtype=np.float32).squeeze()
    if samples.ndim != 1 or len(samples) < rate * .1 or not np.all(np.isfinite(samples)):
        raise RuntimeError("Invalid synthesis output")
    buf = io.BytesIO()
    sf.write(buf, samples, rate, format="WAV", subtype="PCM_16")
    return buf.getvalue(), rate, round((time.perf_counter() - start) * 1000)


@app.post("/tts")
async def tts(body: SynthesisRequest, request: Request):
    global pending
    if not status["ready"]:
        raise HTTPException(503, "TTS model is not ready")
    if pending >= 4:
        raise HTTPException(429, "TTS queue is full")
    pending += 1
    try:
        async with queue:
            if await request.is_disconnected():
                raise HTTPException(499, "Request canceled before synthesis")
            # An in-flight non-streaming generation finishes; canceled queued jobs never start.
            audio, rate, elapsed = await asyncio.to_thread(synthesize, body.text)
            if await request.is_disconnected():
                raise HTTPException(499, "Request canceled during synthesis")
            return Response(audio, media_type="audio/wav", headers={
                "X-Inference-Ms": str(elapsed), "X-Model": REPO,
                "X-Model-Revision": REVISION, "X-Voice": VOICE, "X-Sample-Rate": str(rate),
            })
    finally:
        pending -= 1
