"""P1.1 统一登录 L1/L2 测试：双令牌 + 共享域 Cookie + Cookie 鉴权。

覆盖：
- login 返回 {token, refresh, role}
- 登录响应写共享域 access Cookie（yika_access）
- 发 refresh → 旋转出新 access + 更新 Cookie
- get_current_user 支持从 Cookie 鉴权（iframe 子系统场景）
- 失效 token 返回 401
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register(client, username="dev_auth1", role="developer"):
    client.post("/auth/register", json={"username": username, "password": "pw123456", "role": role})


def test_login_returns_dual_token_and_cookie(client):
    _register(client)
    r = client.post("/auth/login", json={"username": "dev_auth1", "password": "pw123456"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body and body["token"]
    assert "refresh" in body and body["refresh"]
    assert body["role"] == "developer"
    # 共享域 Cookie 已写入
    assert settings.cookie_name in r.cookies
    assert r.cookies[settings.cookie_name]


def test_refresh_rotates_and_updates_cookie(client):
    _register(client)
    lg = client.post("/auth/login", json={"username": "dev_auth1", "password": "pw123456"})
    refresh_tok = lg.json()["refresh"]
    r = client.post("/auth/refresh", json={"refresh": refresh_tok})
    assert r.status_code == 200
    assert "token" in r.json() and "refresh" in r.json()
    assert settings.cookie_name in r.cookies  # Cookie 被更新


def test_cookie_auth_works_for_protected_route(client):
    """无 header、仅 Cookie 也能访问需登录接口（iframe 共享登录态）。"""
    _register(client)
    client.post("/auth/login", json={"username": "dev_auth1", "password": "pw123456"})
    # TestClient 已保存 cookie；不带 Authorization header 访问需登录接口
    r = client.get("/requirements/")
    assert r.status_code == 200  # 靠 Cookie 鉴权通过


def test_invalid_token_401(client):
    r = client.get("/requirements/", headers={"token": "not-a-real-token"})
    assert r.status_code == 401
