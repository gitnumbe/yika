"""后台任务：用线程池执行录音后处理流水线，避免阻塞请求。"""
import threading

from .database import SessionLocal
from .services.pipeline import process_recording


def run_pipeline(recording_id: int):
    db = SessionLocal()
    try:
        process_recording(db, recording_id)
    finally:
        db.close()


def start_pipeline(recording_id: int):
    threading.Thread(target=run_pipeline, args=(recording_id,), daemon=True).start()
