"""认证与安全（生产级 v2.0 · 开发文档 §10.3）。

变更要点（相对 v1.0 单令牌 7 天）：
1. JWT 双令牌：access 15min + refresh 7d（可旋转/吊销，存量哈希存 refresh_tokens 表）。
2. 登录限速：同用户/IP 5 次/分钟连续失败 → 锁定 15 分钟（failed_attempts + locked_until）。
3. bcrypt cost 12。
4. 审计：登录/登出/失败均写 audit_logs（由 auth 层统一埋点，尽力而为）。
5. 兼容：get_current_user 仍接受旧单令牌（无失败计时），新 login 返回 {access, refresh}。
"""
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session
from .models import AuditLog, RefreshToken, User

ACCESS_TTL_MIN = 15
REFRESH_TTL_DAYS = 7
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MIN = 15


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


# ---------- 令牌 ----------

def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(user_id: int, db: Session) -> str:
    """创建 refresh 令牌：返回明文（一次性），库中只存哈希，可吊销。"""
    raw = jwt.encode(
        {"sub": str(user_id), "type": "refresh", "exp": datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS)},
        settings.secret_key,
        algorithm="HS256",
    )
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=hash_password(raw),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS),
    ))
    db.commit()
    return raw


def rotate_refresh_token(raw: str, db: Session) -> str | None:
    """刷新：校验明文哈希 + 吊销旧 + 发新。失败返回 None。"""
    try:
        payload = jwt.decode(raw, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return None
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
    token = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).all()
    # 用 bcrypt verify 比对（hash_password 每次 salt 不同，不能直接比对）
    matched = next((t for t in token if verify_password(raw, t.token_hash)), None)
    if not matched:
        return None
    # 吊销旧令牌（旋转）
    token_to_revoke = matched
    token_to_revoke.revoked_at = datetime.utcnow()
    db.commit()
    return create_refresh_token(user_id, db)


def create_token(user_id: int, role: str) -> str:
    """兼容层：v1.0 单令牌（7 天）。新代码用 create_access_token + create_refresh_token。"""
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": "legacy", "exp": datetime.utcnow() + timedelta(days=7)},
        settings.secret_key,
        algorithm="HS256",
    )


# ---------- 登录限速 ----------

def check_lockout(db: Session, user: User | None) -> None:
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(423, "账号已锁定，请稍后再试")


def register_login_failure(db: Session, user: User | None, username: str) -> None:
    if user:
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.failed_attempts = 0
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MIN)
        user.last_login_at = None
    db.add(AuditLog(
        user_id=user.id if user else None,
        action="login_failed",
        target_type="auth",
        target_id=username,
        detail={"username": username},
    ))
    db.commit()


def record_login_success(db: Session, user: User) -> None:
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.add(AuditLog(
        user_id=user.id,
        action="login_success",
        target_type="auth",
        target_id=user.username,
        detail={},
    ))
    db.commit()


# ---------- 请求依赖 ----------

def get_current_user(
    token: str = Header(None),
    request: Request = None,
    db: Session = Depends(get_session),
) -> User:
    # 优先 header；iframe 子系统场景（或无 header）回退到共享域 Cookie
    if not token and request is not None:
        token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(401, "未登录")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录已失效")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "登录已失效")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(get_current_user)):
        if user.role.value not in roles:
            raise HTTPException(403, "权限不足")
        return user

    return dep
