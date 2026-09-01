from fastapi import APIRouter, Body, Depends, HTTPException
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
    # 限速：先查锁定，再验密（防暴力枚举）
    auth.check_lockout(db, user)
    if not user or not auth.verify_password(body.password, user.password_hash):
        auth.register_login_failure(db, user, body.username)
        raise HTTPException(401, "用户名或密码错误")
    auth.record_login_success(db, user)
    return TokenOut(token=auth.create_token(user.id, user.role.value), role=user.role.value)


@router.post("/refresh")
def refresh(raw: dict = Body(...), db: Session = Depends(get_session)):
    """刷新令牌（生产级双令牌）：旧 refresh 带过来 → 校验 → 旋转发新对。"""
    token_str = raw.get("refresh") or ""
    new_refresh = auth.rotate_refresh_token(token_str, db)
    if not new_refresh:
        raise HTTPException(401, "刷新令牌无效")
    # 从旧令牌取 sub 发新 access
    import jwt
    from ..config import settings
    try:
        payload = jwt.decode(token_str, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(401, "用户不存在")
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "刷新令牌无效")
    access = auth.create_access_token(user.id, user.role.value)
    return {"access": access, "refresh": new_refresh}
