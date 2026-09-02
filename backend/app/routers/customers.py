from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Customer, User
from ..schemas import CustomerIn, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    return db.query(Customer).all()


@router.post("/", response_model=CustomerOut)
def create_customer(body: CustomerIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    c = Customer(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
