import os
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .. import tasks
from ..auth import require_role
from ..database import get_session
from ..models import Recording, User

router = APIRouter(prefix="/recordings", tags=["recordings"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
def upload(
    audio: UploadFile = File(...),
    customer_id: int | None = Form(None),
    project_id: int | None = Form(None),
    scene: str = Form("internal"),
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "developer", "instructor", "leader")),
):
    # P6.4：customer 组隔离校验（customer 必须属于当前用户组，或 admin 全局）
    resolved_customer_id = customer_id
    if customer_id:
        from ..models import Customer
        cust = db.get(Customer, customer_id)
        if not cust:
            return {"error": "customer not found"}
        group_ids = user.group_ids or []
        if user.role != "admin" and cust.group_id not in group_ids:
            return {"error": "cross-group customer forbidden"}

    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.webm")
    with open(path, "wb") as f:
        f.write(audio.file.read())
    rec = Recording(
        customer_id=resolved_customer_id,
        project_id=project_id,
        scene=scene,
        audio_path=path,
        author_id=user.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    tasks.start_pipeline(rec.id)
    return {"id": rec.id, "status": rec.status}


@router.get("/{rec_id}/status")
def status(rec_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    rec = db.get(Recording, rec_id)
    if not rec:
        return {"error": "not found"}
    return {"id": rec.id, "status": rec.status, "transcript": rec.transcript}
