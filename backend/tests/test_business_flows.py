"""L3 业务闭环测试：跨模块的完整业务流。

覆盖系统的两条核心业务闭环，验证"端到端"的业务逻辑正确性，
而不是单个接口的行为。这些测试的失败意味着业务流程断了，而非某个函数错了。
"""
import pytest

pytestmark = pytest.mark.l3


def _register(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


# ─────────────────────────────────────────────────────────────
# 闭环一：需求全生命周期（讲师提出 → 技术评审 → 开发 → 交付）
# ─────────────────────────────────────────────────────────────
def test_requirement_full_lifecycle(client):
    """需求从草稿到交付的完整闭环，覆盖所有关键状态。"""
    inst_token = _register(client, "讲师小A", "instructor")
    tech_token = _register(client, "技术小B", "tech")
    ih = {"token": inst_token}
    th = {"token": tech_token}

    # 讲师提出需求（草稿）
    r = client.post("/requirements/", json={"title": "自动回复客户咨询"}, headers=ih).json()
    rid = r["id"]
    assert r["status"] == "draft"

    # 技术提交评审 → 判定可行
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th)
    client.post(f"/requirements/{rid}/transition", json={"to": "feasible"}, headers=th)

    # 开始开发 → 交付
    client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"}, headers=th)
    final = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=th)
    assert final.json()["status"] == "delivered"

    # 交付后是终态，不能再流转
    again = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th)
    assert again.status_code == 400


def test_requirement_adjust_and_reopen_closed_loop(client):
    """需求「信息待补充 → 重提 → 不可行 → 重新评估 → 交付」的闭环。"""
    inst_token = _register(client, "讲师C", "instructor")
    tech_token = _register(client, "技术D", "tech")
    ih = {"token": inst_token}
    th = {"token": tech_token}

    rid = client.post("/requirements/", json={"title": "智能推荐功能"}, headers=ih).json()["id"]

    # 提交评审 → 信息待补充（返讲师）
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th)
    client.post(f"/requirements/{rid}/transition", json={"to": "info_needed", "reason": "需确认推荐范围"}, headers=th)

    # 讲师补充后重提 → 评审判不可行（附原因）
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th)
    r = client.post(f"/requirements/{rid}/transition", json={"to": "infeasible", "reason": "技术边界外"}, headers=th)
    assert r.json()["infeasible_reason"] == "技术边界外"

    # 重新评估 → 可行 → 交付（技术边界变化后复活）
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th)
    client.post(f"/requirements/{rid}/transition", json={"to": "feasible"}, headers=th)
    client.post(f"/requirements/{rid}/transition", json={"to": "in_dev"}, headers=th)
    final = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=th)
    assert final.json()["status"] == "delivered"


# ─────────────────────────────────────────────────────────────
# 闭环二：答疑闭环（讲师提问 → 检索 → 转技术 → 作答回流 → 下次自动答）
# ─────────────────────────────────────────────────────────────
def test_qa_knowledge_flywheel_closed_loop(client):
    """验证答疑 agent 的「越用越厚」飞轮：未命中 → 转技术 → 回流 → 下次命中。"""
    inst_token = _register(client, "讲师E", "instructor")
    tech_token = _register(client, "技术F", "tech")
    ih = {"token": inst_token}
    th = {"token": tech_token}

    # 讲师第一次提问：知识库为空，未命中，转技术
    ask1 = client.post("/qa/ask", json={"question": "如何把 agent 部署到内网"}, headers=ih).json()
    assert ask1["needs_human"] is True

    # 技术作答（自动回流知识库）
    qid = ask1["id"]
    client.post(f"/qa/{qid}/answer", json={"answer": "用 Docker 部署，映射端口即可"}, headers=th)

    # 讲师再次提问同样问题：命中知识库，直接答，不再转人工
    ask2 = client.post("/qa/ask", json={"question": "如何把 agent 部署到内网"}, headers=ih).json()
    assert ask2["needs_human"] is False
    assert "Docker" in ask2["answer"]


def test_qa_answer_reflow_persists_across_questions(client):
    """技术人员作答后，知识库新增条目，且能被讲师检索到。"""
    inst_token = _register(client, "讲师G", "instructor")
    tech_token = _register(client, "技术H", "tech")
    ih = {"token": inst_token}
    th = {"token": tech_token}

    qid = client.post("/qa/ask", json={"question": "什么是向量数据库"}, headers=ih).json()["id"]
    client.post(f"/qa/{qid}/answer", json={"answer": "用于存储和检索向量的数据库"}, headers=th)

    # 知识库应有回流条目（讲师只读可见）
    kb = client.get("/knowledge/", headers=ih).json()
    assert any("向量数据库" in k["title"] for k in kb)


# ─────────────────────────────────────────────────────────────
# 闭环三：权限边界闭环（角色权限在端到端流程中不被突破）
# ─────────────────────────────────────────────────────────────
def test_role_permission_boundary_closed_loop(client):
    """验证权限边界贯穿整个流程：讲师不能做技术才能做的事。"""
    inst_token = _register(client, "讲师I", "instructor")
    tech_token = _register(client, "技术J", "tech")
    ih = {"token": inst_token}
    th = {"token": tech_token}

    # 讲师建需求 OK
    rid = client.post("/requirements/", json={"title": "测试需求"}, headers=ih).json()["id"]

    # 讲师不能流转（403）
    r1 = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=ih)
    assert r1.status_code == 403

    # 讲师不能写知识库（403）
    r2 = client.post("/knowledge/", json={"title": "x", "content": "y"}, headers=ih)
    assert r2.status_code == 403

    # 讲师不能导出备份（403）
    r3 = client.get("/backup/export", headers=ih)
    assert r3.status_code == 403

    # 技术都能做（200）
    assert client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=th).status_code == 200
    assert client.post("/knowledge/", json={"title": "y", "content": "z"}, headers=th).status_code == 200
