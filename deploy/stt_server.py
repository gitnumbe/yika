"""STT 推理服务：Qwen3-ASR-1.7B（本地部署）
遵循开发文档 §5.1 契约：POST /v1/transcribe → {text, segments, language, duration_s, quality}

启动：.venv-voice/Scripts/python.exe stt_server.py [--port 8051]
模型：Qwen/Qwen3-ASR-1.7B-hf（D:/models/yika/asr/qwen3-asr-1.7b）
"""
import argparse
import io
import os
import tempfile

import torch
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

MODEL_DIR = os.environ.get("ASR_MODEL_DIR", r"D:/models/yika/asr/qwen3-asr-1.7b")

app = FastAPI(title="yika STT Service", version="1.0")
_model = None


def load_model():
    global _model
    if _model is not None:
        return _model
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    print(f"[stt] loading model from {MODEL_DIR} ...")
    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL_DIR,
        torch_dtype=torch.float32,  # CPU：无 GPU 用 float32；GPU 改 bfloat16 + device_map="auto"
        device_map="cpu",
    )
    model.eval()
    _model = (processor, model)
    print("[stt] model ready")
    return _model


class TranscribeResp(BaseModel):
    text: str
    segments: list[dict]
    language: str
    duration_s: float
    quality: dict


@app.post("/v1/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(default=None),
):
    processor, model = load_model()
    data = await file.read()
    if not data:
        return JSONResponse(status_code=400, content={"error": "empty audio"})

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        # Transformers 原生调用（Qwen3-ASR 官方方式）
        import numpy as np
        import soundfile as sf

        audio, sr = sf.read(tmp_path)
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        duration_s = float(len(audio) / sr)
        audio_list = [audio, sr]

        inputs = processor.apply_transcription_request(
            audio_list, language=[None, language or None]
        ).to("cpu")
        output_ids = model.generate(
            inputs["input_ids"],
            attention_mask=inputs.get("attention_mask"),
            max_new_tokens=1024,
        )
        gen = output_ids[:, inputs["input_ids"].shape[1]:]
        text = processor.decode(gen[0], skip_special_tokens=True)

        segs = []
        if text:
            # 粗分段：按句号/问号切分（时间戳需 forced aligner，MVP 用文本段代替）
            import re
            parts = [s.strip() for s in re.split(r"(?<=[。？！；])", text) if s.strip()]
            n = len(parts)
            for i, p in enumerate(parts):
                segs.append({
                    "start": round(duration_s * i / max(n, 1), 3),
                    "end": round(duration_s * (i + 1) / max(n, 1), 3),
                    "text": p,
                    "confidence": 0.0,  # MVP：置信度字段占位，正式版接 ForcedAligner
                })

        return TranscribeResp(
            text=text,
            segments=segs,
            language=language or "zh",
            duration_s=round(duration_s, 3),
            quality={"low_confidence_ratio": 0.0},
        )
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8051)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    # 预热（避免首次请求加载 3.9G 权重超时）
    load_model()
    uvicorn.run(app, host=args.host, port=args.port)
