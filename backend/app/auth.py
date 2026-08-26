from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session
from .models import User


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_current_user(token: str = Header(None), db: Session = Depends(get_session)) -> User:
    if not token:
        raise HTTPException(401, "未登录")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录已失效")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(get_current_user)):
        if user.role.value not in roles:
            raise HTTPException(403, "权限不足")
        return user

    return dep
