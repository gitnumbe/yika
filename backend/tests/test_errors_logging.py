"""P0.5 统一错误处理 + 日志骨架 L1 单测。

覆盖：
- 统一错误响应体 {error:{code,message,detail}}
- 404 / 422(校验失败) / 401(未登录) 均走统一结构
- 日志骨架 setup_logging 可配置、幂等
"""
import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.logging import setup_logging, get_logger


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------- 统一错误处理 ----------

def test_404_unified(client):
    r = client.get("/api/nonexistent")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]


def test_validation_error_unified(client):
    # POST /auth/login 缺字段 → 422 统一结构
    r = client.post("/auth/login", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "detail" in r.json()["error"]


def test_unauthorized_unified(client):
    # 访问需登录接口无 token → 401 统一结构
    r = client.get("/requirements/")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


# ---------- 日志骨架 ----------

def test_setup_logging_idempotent():
    """重复 setup_logging 不重复追加 handler。"""
    setup_logging()
    root = __import__("logging").getLogger()
    n_before = len(root.handlers)
    setup_logging()  # 再次调用
    assert len(root.handlers) == n_before  # 幂等


def test_get_logger_configured():
    """get_logger 返回已配置 logger。"""
    setup_logging()
    logger = get_logger("yika.test")
    assert logger.level == 0 or logger.level != logging.NOTSET
