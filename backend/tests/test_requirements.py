"""P3.3 需求状态机 L2 测试（v3 语义）。

v3：需求挂项目下；开发建需求→submit(draft→待评审)；评审拍板(feasible/info_needed等)=组长专属。
讲师不能做评审流转。
"""
import uuid
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.l2
SUF = uuid.uuid4().hex[:6]


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(c, u="admin", p="admin123"):
    return c.post("/auth/login", json={"username": u, "password": p}).json()["token"]


def _mk_user_in_group(c, admin_tok, uname, role):
    gid = c.post("/org/groups", json={"name": f"req_{uname}_{SUF}"}, headers={"token": admin_tok}).json()["id"]
    c.post("/org/users", json={"username": f"{uname}_{SUF}", "password": "pw123456", "role": role,
                               "group_ids": [gid], "display_name": uname}, headers={"token": admin_tok})
    tok = _login(c, f"{uname}_{SUF}", "pw123456")
    # 组内建客户+项目，返回 (gid, proj_id, tok)
    cid = c.post("/customers/", json={"name": f"客户{uname}_{SUF}"}, headers={"token": tok}).json()["id"]
    pid = c.post("/projects/", json={"name": f"项目{uname}_{SUF}", "customer_id": cid},
                 headers={"token": tok}).json()["id"]
    return gid, pid, tok


def test_full_review_flow(client):
    a = _login(client)
    # 组长建需求走完整状态机
    gid, pid, ltok = _mk_user_in_group(client, a, "reqL", "leader")
    h = {"token": ltok}
    rid = client.post("/requirements/", json={"title": "自动回复客户咨询", "project_id": pid}, headers=h).json()["id"]
    # draft -> pending_review (submit)
    assert client.post(f"/requirements/{rid}/submit", headers=h).json()["status"] == "pending_review"
    # pending_review -> info_needed (组长评审)
    assert client.post(f"/requirements/{rid}/transition", json={"to": "info_needed", "reason": "需向客户确认并发量"}, headers=h).json()["status"] == "info_needed"
    # info_needed -> pending_review
    assert client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h).json()["status"] == "pending_review"


def test_illegal_transition_rejected(client):
    a = _login(client)
    gid, pid, ltok = _mk_user_in_group(client, a, "reqI", "leader")
    h = {"token": ltok}
    rid = client.post("/requirements/", json={"title": "x", "project_id": pid}, headers=h).json()["id"]
    # draft 直接到 delivered → 400
    r = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=h)
    assert r.status_code == 400


def test_instructor_cannot_review(client):
    a = _login(client)
    # 讲师建需求、提交；但评审流转(→feasible) 403
    _, pid, itok = _mk_user_in_group(client, a, "reqC", "instructor")
    hi = {"token": itok}
    rid = client.post("/requirements/", json={"title": "x", "project_id": pid}, headers=hi).json()["id"]
    client.post(f"/requirements/{rid}/submit", headers=hi)
    # 讲师尝试评审拍板 → 403
    r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"}, headers=hi)
    assert r.status_code == 403


def _audit_rows(action, target_id=None):
    con = sqlite3.connect("test.db")
    cur = con.cursor()
    if target_id:
        cur.execute("select action, user_id, target_id, detail from audit_logs where action=? and target_id=?",
                    (action, str(target_id)))
    else:
        cur.execute("select action, user_id, target_id, detail from audit_logs where action=?", (action,))
    rows = cur.fetchall()
    con.close()
    return rows


def test_review_and_deliver_write_audit(client):
    """§12.6：评审(→feasible)、交付(→in_dev/→delivered) 应写 AuditLog。"""
    a = _login(client)
    gid, pid, ltok = _mk_user_in_group(client, a, "reqAudit", "leader")
    h = {"token": ltok}
    rid = client.post("/requirements/", json={"title": "审计测试需求", "project_id": pid}, headers=h).json()["id"]
    client.post(f"/requirements/{rid}/submit", headers=h)
    assert _audit_rows("requirement.submit_review", rid), "提交评审应写审计"
    client.post(f"/requirements/{rid}/transition", json={"to": "feasible", "reason": "评估可行"}, headers=h)
    assert _audit_rows("requirement.review", rid), "组长评审应写审计"
    client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"}, headers=h)
    client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=h)
    assert _audit_rows("requirement.deliver", rid), "开发/交付应写审计"
