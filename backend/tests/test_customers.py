"""P3.1 客户 CRUD + 客户池导入（组私有/组长导入）。

覆盖：
- 组内建客户 → 可见
- 跨组读不到（404/列表不含）→ 组隔离
- 单客户 GET/PUT/DELETE
- 客户池导入：组长可导入、开发 403、跨组不可
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

SUF = uuid.uuid4().hex[:6]
ADMIN = ("admin", "admin123")


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(c, u, p):
    r = c.post("/auth/login", json={"username": u, "password": p})
    return r.json()["token"]


def _mk_group_user(c, admin_tok, gname, uname, role):
    """建唯一组+用户，返回 (gid, token)。"""
    r = c.post("/org/groups", json={"name": f"{gname}_{SUF}"}, headers={"token": admin_tok})
    gid = r.json()["id"]
    c.post("/org/users", json={"username": f"{uname}_{SUF}", "password": "pw123456",
                               "role": role, "group_ids": [gid], "display_name": uname},
           headers={"token": admin_tok})
    return gid, _login(c, f"{uname}_{SUF}", "pw123456")


def test_crud_within_group(client):
    """同组开发建/查/改/删客户。"""
    admin_t = _login(client, "admin", "admin123")
    gid, dtok = _mk_group_user(client, admin_t, "客A", "devA", "developer")
    # 建
    r = client.post("/customers/", json={"name": "甲公司", "industry": "制造", "scale": "大型"},
                    headers={"token": dtok})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    # 查单个
    r = client.get(f"/customers/{cid}", headers={"token": dtok})
    assert r.status_code == 200 and r.json()["name"] == "甲公司"
    # 列表含
    assert any(x["id"] == cid for x in client.get("/customers/", headers={"token": dtok}).json())
    # 改
    r = client.put(f"/customers/{cid}", json={"name": "甲公司改名", "industry": "科技"},
                   headers={"token": dtok})
    assert r.status_code == 200 and r.json()["name"] == "甲公司改名"
    # 删
    assert client.delete(f"/customers/{cid}", headers={"token": dtok}).status_code == 204


def test_cross_group_isolated(client):
    """B 组读不到 A 组客户。"""
    admin_t = _login(client, "admin", "admin123")
    gA, tokA = _mk_group_user(client, admin_t, "客I", "devI", "developer")
    gB, tokB = _mk_group_user(client, admin_t, "客J", "devJ", "developer")
    cid = client.post("/customers/", json={"name": "A组客户"}, headers={"token": tokA}).json()["id"]
    # B 组 GET 单条 → 404（不可见）
    assert client.get(f"/customers/{cid}", headers={"token": tokB}).status_code == 404
    # B 组列表不含
    ids = [x["id"] for x in client.get("/customers/", headers={"token": tokB}).json()]
    assert cid not in ids


def test_import_only_leader_admin(client):
    """客户池导入：组长可、开发 403。"""
    admin_t = _login(client, "admin", "admin123")
    _, ltok = _mk_group_user(client, admin_t, "客K", "lead", "leader")
    _, dtok = _mk_group_user(client, admin_t, "客L", "devL", "developer")
    body = {"customers": [{"name": "池客户X", "industry": "金融"}]}
    # 组长可导入
    r = client.post("/customers/import", json=body, headers={"token": ltok})
    assert r.status_code == 200 and r.json()[0]["source"] == "pool"
    # 开发 403
    r = client.post("/customers/import", json=body, headers={"token": dtok})
    assert r.status_code == 403


def test_no_group_cannot_create(client):
    """无组用户不能建客户（403）。"""
    admin_t = _login(client, "admin", "admin123")
    uname = f"nog_{SUF}"
    client.post("/org/users", json={"username": uname, "password": "pw123456",
                                    "role": "developer", "group_ids": [], "display_name": "无组"},
                headers={"token": admin_t})
    tok = _login(client, uname, "pw123456")
    r = client.post("/customers/", json={"name": "无组客户"}, headers={"token": tok})
    assert r.status_code == 403
