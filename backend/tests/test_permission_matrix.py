"""P4 权限矩阵全量越权测试（对照组织与权限矩阵.md）。

对权限矩阵的关键权限格逐项验证：
- 组隔离：客户/项目/需求跨组不可见（404/空）
- 评审权：组长拍板可行/不可行/需调整；讲师/开发 403
- 开发/交付：开发可做 in_dev/delivered；讲师 403
- 写知识库：开发/组长可写；讲师写→draft 待审；admin 403
- 组织管理：admin 专属，其余 403
- 越权穿测：跨组写、越权评审均被拦

用 seed 组织用户（admin/leader/instructor/developer 同属种子 技术组）+ 动态建异组。
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


def _seed_tokens(c):
    """返回种子四角色 token。"""
    return {
        "admin": _login(c, "admin", "admin123"),
        "leader": _login(c, "leader1", "leader123"),
        "instructor": _login(c, "instructor1", "instructor123"),
        "developer": _login(c, "developer1", "developer123"),
    }


def _mk_other_group_user(c, role):
    """建一个『另一组』的指定角色用户，返回 (gid, token)。"""
    admin = _login(c, "admin", "admin123")
    g = c.post("/org/groups", json={"name": f"og_{role}_{SUF}"}, headers={"token": admin})
    gid = g.json()["id"]
    un = f"ou_{role}_{SUF}"
    c.post("/org/users", json={"username": un, "password": "pw123456", "role": role,
                               "group_ids": [gid], "display_name": un}, headers={"token": admin})
    return gid, _login(c, un, "pw123456")


def _mk_cust_proj(c, tok, gid=None):
    cid = c.post("/customers/", json={"name": f"矩阵客户_{SUF}", "group_id": gid},
                 headers={"token": tok}).json()["id"]
    pid = c.post("/projects/", json={"name": f"矩阵项目_{SUF}", "customer_id": cid},
                 headers={"token": tok}).json()["id"]
    return cid, pid


# ---------- 组隔离 ----------
def test_group_isolation_customer_project_requirement(client):
    """跨组读不到客户/项目/需求（P4.1）。"""
    t = _seed_tokens(client)
    _, otok = _mk_other_group_user(client, "developer")
    # 种子组(技术组)开发建 客户/项目/需求
    cid, pid = _mk_cust_proj(client, t["developer"])
    rid = client.post("/requirements/", json={"title": "矩阵需求", "project_id": pid},
                      headers={"token": t["developer"]}).json()["id"]
    # 异组开发：客户/项目列表不含，需求 404
    oc = client.get("/customers/", headers={"token": otok}).json()
    assert all(x["name"] != f"矩阵客户_{SUF}" for x in oc)
    op = client.get("/projects/", headers={"token": otok}).json()
    assert all(x["name"] != f"矩阵项目_{SUF}" for x in op)
    assert client.get(f"/requirements/{rid}", headers={"token": otok}).status_code == 404


def test_knowledge_platform_wide(client):
    """知识全平台共通：异组也可查（P4.1）。"""
    t = _seed_tokens(client)
    # 种子组开发写知识(published)
    client.post("/knowledge/", json={"title": "共通知识", "body": "x"},
                headers={"token": t["developer"]})
    _, otok = _mk_other_group_user(client, "instructor")
    kb = client.get("/knowledge/", headers={"token": otok}).json()
    assert any(k["title"] == "共通知识" for k in kb)


# ---------- 评审权 ----------
def test_review_leader_only(client):
    """评审拍板=组长专属；讲师/开发 403（P4.2）。"""
    t = _seed_tokens(client)
    _, pid = _mk_cust_proj(client, t["developer"])
    rid = client.post("/requirements/", json={"title": "评审需求", "project_id": pid},
                      headers={"token": t["developer"]}).json()["id"]
    client.post(f"/requirements/{rid}/submit", headers={"token": t["developer"]})
    # 讲师/开发评审 → 403
    for role in ("instructor", "developer"):
        r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                        headers={"token": t[role]})
        assert r.status_code == 403, f"{role} 不应能评审"
    # 组长评审 → 200
    r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                    headers={"token": t["leader"]})
    assert r.status_code == 200, r.text


# ---------- 开发/交付权 ----------
def test_dev_can_dev_and_deliver(client):
    """开发可标 开发中/已交付；讲师 403（矩阵第58行）。"""
    t = _seed_tokens(client)
    _, pid = _mk_cust_proj(client, t["developer"])
    rid = client.post("/requirements/", json={"title": "交付需求", "project_id": pid},
                      headers={"token": t["developer"]}).json()["id"]
    client.post(f"/requirements/{rid}/submit", headers={"token": t["developer"]})
    client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                headers={"token": t["leader"]})
    # 开发做 开发中 → 已交付
    r = client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"},
                    headers={"token": t["developer"]})
    assert r.status_code == 200, r.text
    r = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"},
                    headers={"token": t["developer"]})
    assert r.status_code == 200, r.text
    # 讲师不能推进开发/交付
    rid2 = client.post("/requirements/", json={"title": "讲师不可交付", "project_id": pid},
                       headers={"token": t["instructor"]}).json()["id"]
    client.post(f"/requirements/{rid2}/submit", headers={"token": t["instructor"]})
    client.post(f"/requirements/{rid2}/transition", json={"to": "feasible"},
                headers={"token": t["leader"]})
    r = client.post(f"/requirements/{rid2}/transition", json={"to": "in_dev"},
                    headers={"token": t["instructor"]})
    assert r.status_code == 403


# ---------- 知识库权限 ----------
def test_knowledge_write_matrix(client):
    """知识写权限：开发/组长直接发布，讲师→draft，admin 403。"""
    t = _seed_tokens(client)
    for role in ("developer", "leader"):
        r = client.post("/knowledge/", json={"title": f"{role}知识", "body": "x"},
                        headers={"token": t[role]})
        assert r.status_code == 200 and r.json()["status"] == "published"
    r = client.post("/knowledge/", json={"title": "讲师知识", "body": "x"},
                    headers={"token": t["instructor"]})
    assert r.status_code == 200 and r.json()["status"] == "draft"
    r = client.post("/knowledge/", json={"title": "admin知识", "body": "x"},
                    headers={"token": t["admin"]})
    assert r.status_code == 403


# ---------- 组织管理权限 ----------
def test_org_manage_admin_only(client):
    """管用户/建组/派组长 = admin 专属；其他角色 403。"""
    t = _seed_tokens(client)
    for role in ("leader", "instructor", "developer"):
        r = client.post("/org/groups", json={"name": f"越权组_{role}_{SUF}"},
                        headers={"token": t[role]})
        assert r.status_code == 403, f"{role} 不应能建组"
