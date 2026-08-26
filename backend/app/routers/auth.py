from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_session
from ..models import Role, User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_session)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    if body.role not in [r.value for r in Role]:
        raise HTTPException(400, "非法角色")
    user = User(username=body.username, password_hash=auth.hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=auth.create_token(user.id, user.role.value), role=user.role.value)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return TokenOut(token=auth.create_token(user.id, user.role.value), role=user.role.value)
