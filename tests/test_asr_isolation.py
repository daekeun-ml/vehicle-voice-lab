"""ASR must not acquire or replace the direct-audio model's process lock."""
import asyncio
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"runtime"))
import speech_manager as manager
from fastapi import HTTPException, UploadFile

class Request:
    async def is_disconnected(self):
        return False

class Response:
    status_code = 200
    def json(self):
        return {"ready": True, "text": "조수석 24도", "elapsedMs": 1}

class Client:
    calls = []
    active = {}
    peak = {}
    def __init__(self, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def get(self, url, **kwargs):
        return Response()
    async def post(self, url, **kwargs):
        self.calls.append(url)
        self.active[url] = self.active.get(url, 0)+1
        self.peak[url] = max(self.peak.get(url, 0), self.active[url])
        await asyncio.sleep(.02)
        self.active[url] -= 1
        return Response()

class AsrIsolation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        manager.gate = asyncio.Lock()
        manager.asr_queues = {m: asyncio.Lock() for m in manager.ASR_MODELS}
        manager.asr_pending = {m: 0 for m in manager.ASR_MODELS}
        Client.calls, Client.active, Client.peak = [], {}, {}
        self.mock = patch.object(manager.httpx, "AsyncClient", Client)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    async def recognize(self, model):
        return await manager.run("asr", Request(), UploadFile(file=io.BytesIO(b"wav")),
                                 model_id=model)

    async def test_active_omni_lock_does_not_block_either_asr(self):
        async with manager.gate:
            for model, port in manager.ASR_MODELS.items():
                response = await self.recognize(model)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.body)["independentAsr"])
                self.assertIn(f":{port}/asr", Client.calls[-1])
                self.assertTrue(manager.gate.locked())

    async def test_same_model_serializes_and_releases_pending_count(self):
        await asyncio.gather(*(self.recognize("qwen3-asr-06b") for _ in range(3)))
        self.assertEqual(Client.peak["http://127.0.0.1:9116/asr"], 1)
        self.assertEqual(manager.asr_pending["qwen3-asr-06b"], 0)

    async def test_overload_is_bounded_without_calling_worker(self):
        manager.asr_pending["qwen3-asr-06b"] = 4
        with self.assertRaises(HTTPException) as error:
            await self.recognize("qwen3-asr-06b")
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(Client.calls, [])

if __name__ == "__main__":
    unittest.main()
