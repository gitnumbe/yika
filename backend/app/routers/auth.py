from fastapi import APIRouter, Body, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .. import auth
from ..config import settings
from ..database import get_session
from ..models import Role, User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_access_cookie(resp: Response, access: str):
    """把 access 写入共享域 Cookie（供 iframe 子系统共享登录态）。"""
    resp.set_cookie(
        key=settings.cookie_name,
        value=access,
        httponly=True,
        secure=settings.cookie_secure,
        domain=settings.cookie_domain or None,
        samesite="lax",
        max_age=60 * 15,  # access 15min
        path="/",
    )


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
    return TokenOut(token=auth.create_access_token(user.id, user.role.value),
                    refresh=auth.create_refresh_token(user.id, db), role=user.role.value)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.username == body.username).first()
    # 限速：先查锁定，再验密（防暴力枚举）
    auth.check_lockout(db, user)
    if not user or not auth.verify_password(body.password, user.password_hash):
        auth.register_login_failure(db, user, body.username)
        raise HTTPException(401, "用户名或密码错误")
    auth.record_login_success(db, user)
    access = auth.create_access_token(user.id, user.role.value)
    refresh = auth.create_refresh_token(user.id, db)
    _set_access_cookie(response, access)
    return TokenOut(token=access, refresh=refresh, role=user.role.value)


@router.post("/refresh", response_model=TokenOut)
def refresh(raw: dict = Body(...), response: Response = None, db: Session = Depends(get_session)):
    """刷新令牌（生产级双令牌）：旧 refresh 带过来 → 校验 → 旋转发新对 + 更新 Cookie。"""
    import jwt as _jwt
    token_str = raw.get("refresh") or ""
    new_refresh = auth.rotate_refresh_token(token_str, db)
    if not new_refresh:
        raise HTTPException(401, "刷新令牌无效")
    try:
        payload = _jwt.decode(token_str, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(401, "用户不存在")
    except (_jwt.PyJWTError, ValueError):
        raise HTTPException(401, "刷新令牌无效")
    access = auth.create_access_token(user.id, user.role.value)
    _set_access_cookie(response, access)
    return TokenOut(token=access, refresh=new_refresh, role=user.role.value)
