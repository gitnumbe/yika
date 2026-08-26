from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import state_machine
from ..auth import require_role
from ..database import get_session
from ..models import ReqStatus, Requirement, User
from ..schemas import RequirementIn, TransitionIn

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.post("/")
def create_requirement(body: RequirementIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    r = Requirement(**body.model_dump(), author_id=user.id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "status": r.status.value, "title": r.title}


@router.get("/")
def list_requirements(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return [{"id": r.id, "title": r.title, "status": r.status.value, "project_id": r.project_id} for r in db.query(Requirement).all()]


@router.post("/{req_id}/transition")
def transition_requirement(req_id: int, body: TransitionIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech"))):
    r = db.get(Requirement, req_id)
    if not r:
        raise HTTPException(404, "需求不存在")
    try:
        state_machine.transition(r, ReqStatus(body.to), body.reason)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"id": r.id, "status": r.status.value, "infeasible_reason": r.infeasible_reason}
