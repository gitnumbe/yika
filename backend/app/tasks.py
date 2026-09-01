"""后台任务：线程池执行录音后处理流水线（生产级 §8.6）。

重试/幂等：
- 失败 attempts+1，指数退避（1min → 5min → 15min）写入 retry_at；
- 3 次后置 failed 并记录 last_error（不再重试，人工介入）；
- 同 recording_id 同 stage 幂等：running 状态不重复启动。
"""
import threading
import time
from datetime import datetime, timedelta

from .database import SessionLocal
from .models import ProcessingTask
from .services.pipeline import process_recording

MAX_ATTEMPTS = 3
BACKOFF = [1, 5, 15]  # 分钟


def run_pipeline(recording_id: int) -> None:
    """执行流水线（含重试记录）。幂等：若已有相同 recording 的 running/failed 任务则跳过。"""
    db = SessionLocal()
    try:
        task = db.query(ProcessingTask).filter(
            ProcessingTask.recording_id == recording_id,
            ProcessingTask.stage == "pipeline",
        ).first()
        if task and task.status in ("running", "done"):
            return
        if not task:
            task = ProcessingTask(recording_id=recording_id, stage="pipeline", status="running")
            db.add(task)
            db.commit()
        else:
            task.status = "running"
            task.last_error = ""
            db.commit()

        try:
            process_recording(db, recording_id)
            task.status = "done"
            db.commit()
        except Exception as e:  # noqa: BLE001
            task.attempts += 1
            task.last_error = f"{type(e).__name__}: {str(e)[:500]}"
            if task.attempts >= MAX_ATTEMPTS:
                task.status = "failed"
            else:
                task.status = "pending"
                # 指数退避：attempts=1→1min, 2→5min（15min 留给第 3 次）
                delay = BACKOFF[min(task.attempts - 1, len(BACKOFF) - 1)]
                task.retry_at = datetime.utcnow() + timedelta(minutes=delay)
            db.commit()
    finally:
        db.close()


def start_pipeline(recording_id: int) -> None:
    threading.Thread(target=run_pipeline, args=(recording_id,), daemon=True).start()


def retry_due_tasks() -> None:
    """扫描到期的 pending 任务重跑（可挂 cron 每分钟）。"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due = db.query(ProcessingTask).filter(
            ProcessingTask.status == "pending",
            (ProcessingTask.retry_at.is_(None)) | (ProcessingTask.retry_at <= now),
        ).all()
        for t in due:
            t.status = "running"
            db.commit()
            threading.Thread(target=run_pipeline, args=(t.recording_id,), daemon=True).start()
    finally:
        db.close()
