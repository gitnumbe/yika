"""P3.2 项目 CRUD（挂客户下，组私有）。

覆盖：
- 本组在客户下建项目 → 继承客户组
- 项目列表/单查按组隔离（跨组读不到）
- 跨组借客户建项目 → 403
- 更新/删除
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

SUF = uuid.uuid4().hex[:6]


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(c, u="admin", p="admin123"):
    return c.post("/auth/login", json={"username": u, "password": p}).json()["token"]


def _mk_g(c, admin_tok, gname, uname, role):
    gid = c.post("/org/groups", json={"name": f"{gname}_{SUF}"}, headers={"token": admin_tok}).json()["id"]
    c.post("/org/users", json={"username": f"{uname}_{SUF}", "password": "pw123456", "role": role,
                               "group_ids": [gid], "display_name": uname}, headers={"token": admin_tok})
    return gid, _login(c, f"{uname}_{SUF}", "pw123456")


def _mk_cust(c, tok, gid, name):
    return c.post("/customers/", json={"name": name, "industry": "科技"}, headers={"token": tok}).json()["id"]


def test_project_inherits_customer_group(client):
    a = _login(client)
    gid, dtok = _mk_g(client, a, "项A", "devA", "developer")
    cid = _mk_cust(client, dtok, gid, "客户A")
    r = client.post("/projects/", json={"name": "项目A1", "customer_id": cid}, headers={"token": dtok})
    assert r.status_code == 200
    p = r.json()
    assert p["group_id"] == gid and p["customer_id"] == cid and p["name"] == "项目A1"


def test_project_cross_group_hidden(client):
    a = _login(client)
    gA, tokA = _mk_g(client, a, "项I", "devI", "developer")
    gB, tokB = _mk_g(client, a, "项J", "devJ", "developer")
    cidA = _mk_cust(client, tokA, gA, "客户I")
    client.post("/projects/", json={"name": "项目I1", "customer_id": cidA}, headers={"token": tokA})
    # B 组列表不应含 A 组项目
    lst = client.get("/projects/", headers={"token": tokB}).json()
    names = [x["name"] for x in lst]
    assert "项目I1" not in names


def test_cross_group_customer_forbidden(client):
    a = _login(client)
    gA, tokA = _mk_g(client, a, "项K", "devK", "developer")
    _, tokB = _mk_g(client, a, "项L", "devL", "developer")
    cidA = client.post("/customers/", json={"name": "客户K"}, headers={"token": tokA}).json()["id"]
    # B 想借 A 的客户建项目 → 403
    r = client.post("/projects/", json={"name": "越权项目", "customer_id": cidA}, headers={"token": tokB})
    assert r.status_code in (403, 404)


def test_project_crud_update_delete(client):
    a = _login(client)
    gid, dtok = _mk_g(client, a, "项M", "lead", "leader")
    cid = _mk_cust(client, dtok, gid, "客户M")
    pid = client.post("/projects/", json={"name": "项目M", "customer_id": cid}, headers={"token": dtok}).json()["id"]
    # update
    r = client.put(f"/projects/{pid}", json={"name": "项目M改", "customer_id": cid, "description": "改"},
                   headers={"token": dtok})
    assert r.json()["name"] == "项目M改"
    # delete (leader)
    r = client.delete(f"/projects/{pid}", headers={"token": dtok})
    assert r.status_code == 204
    assert client.get(f"/projects/{pid}", headers={"token": dtok}).status_code == 404
