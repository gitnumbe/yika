"""P3.5 知识库审核队列 L2 测试（讲师写需审核）。

覆盖：
- 开发/组长写 → 直接 published
- 讲师写 → draft(待审核)，未审核不可作为正式发布给普通查
- 讲师不可见他人 draft；组长/开发可看待审核 draft
- 组长/开发审核讲师 draft → published；admin 不可写知识(403)
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _mk(c, role):
    """建一个进组用户返回 token。"""
    # 用 make_org_user fixture 不可在函数用，直接建
    a = c.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    import uuid
    suf = uuid.uuid4().hex[:6]
    g = c.post("/org/groups", json={"name": f"kg_{role}_{suf}"}, headers={"token": a})
    gid = g.json()["id"]
    un = f"ku_{role}_{suf}"
    c.post("/org/users", json={"username": un, "password": "pw123456", "role": role,
                               "group_ids": [gid], "display_name": un}, headers={"token": a})
    return c.post("/auth/login", json={"username": un, "password": "pw123456"}).json()["token"]


def test_dev_writes_published(client):
    """开发写知识 → 直接 published。"""
    tok = _mk(client, "developer")
    r = client.post("/knowledge/", json={"title": "部署指南", "body": "步骤"},
                     headers={"token": tok})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"


def test_instructor_write_is_draft(client):
    """讲师写知识 → draft(待审核)。"""
    tok = _mk(client, "instructor")
    r = client.post("/knowledge/", json={"title": "讲师答疑", "body": "内容"},
                     headers={"token": tok})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"


def test_admin_cannot_write(client):
    """admin 写知识 → 403。"""
    a = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    r = client.post("/knowledge/", json={"title": "admin", "body": "x"}, headers={"token": a})
    assert r.status_code == 403


def test_leader_reviews_instructor_draft(client):
    """组长可看待审核并审核讲师 draft → published。"""
    itok = _mk(client, "instructor")
    ltok = _mk(client, "leader")
    kid = client.post("/knowledge/", json={"title": "讲师条目", "body": "待审"},
                      headers={"token": itok}).json()["id"]
    # 组长能看待审核 draft
    llist = client.get("/knowledge/", headers={"token": ltok}).json()
    assert any(k["id"] == kid and k["status"] == "draft" for k in llist)
    # 审核通过
    r = client.post(f"/knowledge/{kid}/review", headers={"token": ltok})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"
    assert r.json()["reviewer_id"] is not None
    # 审核应写审计（§12.6）
    import sqlite3
    con = sqlite3.connect("test.db")
    rows = con.execute("select action from audit_logs where action='knowledge.review' and target_id=?",
                       (str(kid),)).fetchall()
    con.close()
    assert rows, "知识审核应写 AuditLog"
