"""TTS 推理服务：dots.tts-mf（本地部署）
遵循开发文档 §5.6 契约：POST /v1/speak → audio/wav

启动：.venv-voice/Scripts/python.exe tts_server.py [--port 8052]
模型：dots-studio/dots.tts-mf（D:/models/yika/tts/dots-tts-mf）
参考音：TTS_REF_AUDIO + TTS_REF_TEXT（管理员预录）
"""
import argparse
import base64
import io
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

MODEL_DIR = os.environ.get("TTS_MODEL_DIR", r"D:/models/yika/tts/dots-tts-mf")
REF_AUDIO = os.environ.get("TTS_REF_AUDIO", "")
REF_TEXT = os.environ.get("TTS_REF_TEXT", "")

app = FastAPI(title="yika TTS Service", version="1.0")
_runtime = None


def load_runtime():
    global _runtime
    if _runtime is not None:
        return _runtime
    from dots_tts.runtime import DotsTtsRuntime

    print(f"[tts] loading model from {MODEL_DIR} ...")
    _runtime = DotsTtsRuntime.from_pretrained(MODEL_DIR, precision="float32")  # CPU；GPU 用 bfloat16
    print("[tts] model ready")
    return _runtime


class SpeakReq(BaseModel):
    text: str
    voice_ref: str = "default"  # default = REF_AUDIO/REF_TEXT 参考音
    emotion: str = "neutral"


@app.post("/v1/speak")
async def speak(req: SpeakReq):
    runtime = load_runtime()
    text = req.text.strip()
    if not text:
        return Response(status_code=400, content=b'{"error":"empty text"}')
    if len(text) > 2000:
        return Response(status_code=413, content=b'{"error":"text too long, split needed"}')

    try:
        result = runtime.generate(
            text=text,
            prompt_audio_path=REF_AUDIO,
            prompt_text=REF_TEXT,
            num_steps=4,  # dots.tts-mf 推荐 NFE=4
        )
        import numpy as np
        import soundfile as sf

        audio = result["audio"].float().cpu().squeeze().numpy()
        sr = result["sample_rate"]
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="wav")
        wav = buf.getvalue()
        return Response(content=wav, media_type="audio/wav")
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return Response(status_code=500, content=str(e).encode("utf-8"))


@app.get("/health")
def health():
    return {"status": "ok", "runtime_loaded": _runtime is not None, "ref_audio_set": bool(REF_AUDIO)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8052)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    load_runtime()
    uvicorn.run(app, host=args.host, port=args.port)
