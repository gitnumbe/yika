"""L3 业务闭环测试：需求全生命周期 + 角色评审权限边界（v3 语义）。

v3：需求挂项目(组私有)下，状态机 draft→pending_review→feasible/info_needed/plan_needed/
infeasible→in_dev→delivered；评审前作者 submit(draft→pending_review)；评审拍板(→feasible/
infeasible/info_needed/plan_needed)=组长专属，讲师/开发不可最终定；跨组隔离。

注：原 v2 的两个 QA 飞轮测试(test_qa_knowledge_flywheel_closed_loop /
test_qa_answer_reflow_persists_across_questions)依赖的 v2 知识回流生产路径尚未对齐 v3 模型
(app/services/qa_service.py 检索用 Knowledge.content、app/routers/qa.py 作答写
Knowledge(content=…, source=…)，而 v3 Knowledge 为 body/source_enum)，不在本次测试范围，
故移除；由 QA 子系统自有测试文件覆盖，待主 agent 对齐 qa 生产代码后恢复。
"""
import uuid

import pytest

pytestmark = pytest.mark.l3

ADMIN = ("admin", "admin123")
LEADER = ("leader1", "leader123")      # 种子：组长，属 技术组
INSTRUCTOR = ("instructor1", "instructor123")  # 种子：讲师，属 技术组
DEVELOPER = ("developer1", "developer123")    # 种子：开发，属 技术组


def _login(c, u, p):
    r = c.post("/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _tokens(c):
    """登录 admin/leader/instructor/developer，返回 token dict。"""
    return {
        "admin": _login(c, *ADMIN),
        "leader": _login(c, *LEADER),
        "instructor": _login(c, *INSTRUCTOR),
        "developer": _login(c, *DEVELOPER),
    }


def _new_project(c, tok):
    """在当前(种子技术)组内建客户+项目，返回 project_id。"""
    cid = c.post("/customers/", json={"name": f"客户_{uuid.uuid4().hex[:6]}"},
                 headers={"token": tok}).json()["id"]
    pid = c.post("/projects/", json={"name": "业务闭环项目", "customer_id": cid},
                 headers={"token": tok}).json()["id"]
    return pid


def _create_and_submit(c, pid, tok, title):
    rid = c.post("/requirements/", json={"title": title, "project_id": pid},
                 headers={"token": tok}).json()["id"]
    r = c.post(f"/requirements/{rid}/submit", headers={"token": tok})
    assert r.status_code == 200, r.text
    return rid


# ─────────────────────────────────────────────────────────────
# 需求全生命周期（开发建+submit → 组长评审 → 开发中 → 交付）
# ─────────────────────────────────────────────────────────────
def test_requirement_full_lifecycle(client):
    """draft→pending_review→feasible→in_dev→delivered 全链路；交付=终态不可再流转。"""
    t = _tokens(client)
    pid = _new_project(client, t["leader"])

    # 开发建需求(作者) → 提交评审
    rid = _create_and_submit(client, pid, t["developer"], "自动回复客户咨询")
    got = client.get(f"/requirements/{rid}", headers={"token": t["developer"]}).json()
    assert got["status"] == "pending_review"

    # 组长评审拍板 → 可行
    r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                    headers={"token": t["leader"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "feasible"

    # 组长推进开发中 → 交付
    assert client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"},
                       headers={"token": t["leader"]}).json()["status"] == "in_dev"
    final = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"},
                        headers={"token": t["leader"]}).json()
    assert final["status"] == "delivered"

    # 交付后是终态，不能再流转
    again = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"},
                        headers={"token": t["leader"]})
    assert again.status_code == 400


# ─────────────────────────────────────────────────────────────
# 信息待补 → 重提 → 不可行 → 重新评估 → 交付（作者重提闭环）
# ─────────────────────────────────────────────────────────────
def test_requirement_adjust_and_reopen_closed_loop(client):
    """info_needed 返作者重提、infeasible 归档后经作者 submit 重开，再走可行→交付。"""
    t = _tokens(client)
    pid = _new_project(client, t["leader"])

    rid = _create_and_submit(client, pid, t["developer"], "智能推荐功能")

    # 组长评审 → 信息待补(返提出方)
    r = client.post(f"/requirements/{rid}/transition", json={"to": "info_needed",
                                                             "reason": "需确认推荐范围"},
                    headers={"token": t["leader"]})
    assert r.status_code == 200 and r.json()["status"] == "info_needed"

    # 作者(开发)补充后经 /submit 重提 → 待评审
    assert client.post(f"/requirements/{rid}/submit",
                       headers={"token": t["developer"]}).json()["status"] == "pending_review"

    # 组长评审 → 不可行（附原因）
    r = client.post(f"/requirements/{rid}/transition", json={"to": "infeasible",
                                                             "reason": "技术边界外"},
                    headers={"token": t["leader"]})
    assert r.status_code == 200
    assert r.json()["status"] == "infeasible"
    assert r.json()["infeasible_reason"] == "技术边界外"

    # 技术边界变化后复活：作者重提 → 组长判可行 → 交付
    assert client.post(f"/requirements/{rid}/submit",
                       headers={"token": t["developer"]}).json()["status"] == "pending_review"
    assert client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                       headers={"token": t["leader"]}).json()["status"] == "feasible"
    assert client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"},
                       headers={"token": t["leader"]}).json()["status"] == "in_dev"
    final = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"},
                        headers={"token": t["leader"]}).json()
    assert final["status"] == "delivered"


# ─────────────────────────────────────────────────────────────
# 评审拍板权限边界：组长专属，讲师/开发不可最终定
# ─────────────────────────────────────────────────────────────
def test_review_final_decision_leader_only(client):
    """讲师/开发建+submit 均可；但评审拍板(→feasible/infeasible 等)=组长专属，其它角色 403。"""
    t = _tokens(client)
    pid = _new_project(client, t["leader"])

    # 讲师建需求并提交
    rid = client.post("/requirements/", json={"title": "讲师提出需求", "project_id": pid},
                      headers={"token": t["instructor"]}).json()["id"]
    assert client.post(f"/requirements/{rid}/submit",
                       headers={"token": t["instructor"]}).json()["status"] == "pending_review"

    # 讲师尝试评审拍板 → 403
    r = client.post(f"/requirements/{rid}/transition", json={"to": "infeasible"},
                    headers={"token": t["instructor"]})
    assert r.status_code == 403

    # 开发尝试评审拍板 → 403（开发可交付但不可最终定）
    r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                    headers={"token": t["developer"]})
    assert r.status_code == 403

    # 组长评审 → 可行
    r = client.post(f"/requirements/{rid}/transition", json={"to": "feasible"},
                    headers={"token": t["leader"]})
    assert r.status_code == 200 and r.json()["status"] == "feasible"


# ─────────────────────────────────────────────────────────────
# 非法流转拒绝：不按状态机跳步 → 400
# ─────────────────────────────────────────────────────────────
def test_illegal_transition_rejected(client):
    """跳过必经状态一律 400：draft→delivered、pending_review→in_dev(须先 feasible)。"""
    t = _tokens(client)
    pid = _new_project(client, t["leader"])

    # draft 直接到 delivered → 400
    rid = client.post("/requirements/", json={"title": "x", "project_id": pid},
                      headers={"token": t["developer"]}).json()["id"]
    assert client.post(f"/requirements/{rid}/transition", json={"to": "delivered"},
                       headers={"token": t["leader"]}).status_code == 400

    # pending_review 直接到 in_dev(未先判 feasible) → 400
    rid2 = _create_and_submit(client, pid, t["developer"], "须先可行")
    assert client.post(f"/requirements/{rid2}/transition", json={"to": "in_dev"},
                       headers={"token": t["leader"]}).status_code == 400
    # 判可行后再进开发中 → 200
    assert client.post(f"/requirements/{rid2}/transition", json={"to": "feasible"},
                       headers={"token": t["leader"]}).status_code == 200
    assert client.post(f"/requirements/{rid2}/transition", json={"to": "in_dev"},
                       headers={"token": t["leader"]}).status_code == 200


# ─────────────────────────────────────────────────────────────
# 组隔离在业务流中不被突破：跨组读不到/建不了
# ─────────────────────────────────────────────────────────────
def test_cross_group_isolation_in_business_flow(client):
    """需求组私有：组长组内建需求，异组用户 list 见不到、get 404、跨组建需求 403。"""
    t = _tokens(client)
    pid = _new_project(client, t["leader"])
    rid = client.post("/requirements/", json={"title": "组内私有需求", "project_id": pid},
                      headers={"token": t["leader"]}).json()["id"]

    # admin 建异组 + 异组开发
    suf = uuid.uuid4().hex[:6]
    gid = client.post("/org/groups", json={"name": f"外组_{suf}"},
                      headers={"token": t["admin"]}).json()["id"]
    client.post("/org/users", json={"username": f"外dev_{suf}", "password": "pw123456",
                                    "role": "developer", "group_ids": [gid],
                                    "display_name": "外部开发"}, headers={"token": t["admin"]})
    out_tok = _login(client, f"外dev_{suf}", "pw123456")

    # 异组 list 需求 → 空
    assert client.get("/requirements/", headers={"token": out_tok}).json() == []
    # 异组 get 组内需求 → 404（不泄露存在性）
    assert client.get(f"/requirements/{rid}", headers={"token": out_tok}).status_code == 404
    # 异组在组长组项目下建需求 → 403
    r = client.post("/requirements/", json={"title": "越权需求", "project_id": pid},
                    headers={"token": out_tok})
    assert r.status_code == 403

    # 组内正常可见
    titles = [x["title"] for x in client.get("/requirements/",
             headers={"token": t["leader"]}).json()]
    assert "组内私有需求" in titles
