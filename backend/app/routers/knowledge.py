from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Knowledge, User
from ..schemas import KnowledgeIn, KnowledgeOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/", response_model=list[KnowledgeOut])
def list_knowledge(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    return db.query(Knowledge).all()


@router.post("/", response_model=KnowledgeOut)
def create_knowledge(body: KnowledgeIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "leader"))):
    k = Knowledge(**body.model_dump())
    db.add(k)
    db.commit()
    db.refresh(k)
    return k
