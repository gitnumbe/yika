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
    project_id: int | None = Form(None),
    scene: str = Form("internal"),
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "tech", "instructor")),
):
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.webm")
    with open(path, "wb") as f:
        f.write(audio.file.read())
    rec = Recording(project_id=project_id, scene=scene, audio_path=path, author_id=user.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    tasks.start_pipeline(rec.id)
    return {"id": rec.id, "status": rec.status}


@router.get("/{rec_id}/status")
def status(rec_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    rec = db.get(Recording, rec_id)
    if not rec:
        return {"error": "not found"}
    return {"id": rec.id, "status": rec.status, "transcript": rec.transcript}
