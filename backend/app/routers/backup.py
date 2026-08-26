from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Customer, Knowledge, Note, Project, QA, Requirement, User

router = APIRouter(prefix="/backup", tags=["backup"])


def _dump(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/export")
def export(db: Session = Depends(get_session), user=Depends(require_role("admin"))):
    return {
        "users": [_dump(u) for u in db.query(User).all()],
        "customers": [_dump(c) for c in db.query(Customer).all()],
        "projects": [_dump(p) for p in db.query(Project).all()],
        "requirements": [_dump(r) for r in db.query(Requirement).all()],
        "notes": [_dump(n) for n in db.query(Note).all()],
        "knowledge": [_dump(k) for k in db.query(Knowledge).all()],
        "qa": [_dump(q) for q in db.query(QA).all()],
    }
