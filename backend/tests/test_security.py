"""L2 安全基线测试：登录限速锁定 + 审计落库（生产级 §10.3）。"""
import pytest

pytestmark = pytest.mark.l2


def _register(client, username, role="tech"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})


def test_login_failure_locks_account(client):
    """连续 5 次失败 → 账号锁定 15 分钟（423）。"""
    _register(client, "锁定用户")
    for _ in range(5):
        r = client.post("/auth/login", json={"username": "锁定用户", "password": "wrong"})
        assert r.status_code == 401
    # 第 6 次：即使密码正确也锁定
    r = client.post("/auth/login", json={"username": "锁定用户", "password": "pw"})
    assert r.status_code == 423


def test_audit_log_written_on_login(client):
    """登录成功/失败均写 audit_logs（只增不改）。"""
    _register(client, "审计用户")
    client.post("/auth/login", json={"username": "审计用户", "password": "wrong"})
    client.post("/auth/login", json={"username": "审计用户", "password": "pw"})

    # 直接查库验证
    from app.database import SessionLocal
    from app.models import AuditLog
    db = SessionLocal()
    try:
        actions = [a.action for a in db.query(AuditLog).all()]
        assert "login_failed" in actions
        assert "login_success" in actions
    finally:
        db.close()
