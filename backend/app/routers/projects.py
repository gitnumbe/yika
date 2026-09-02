from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Project, User
from ..schemas import ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    return db.query(Project).all()


@router.post("/", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    p = Project(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
