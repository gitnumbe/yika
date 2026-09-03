"""客户→项目（v3）：须进组用户建（组私有）；未登录 401。

v2→v3：无 /auth/register 组内建户，用 make_org_user（admin 经 /org/groups+/org/users 建进组用户）。
create_customer 返回 201（v3 语义）。
"""
import pytest

pytestmark = pytest.mark.l2


def test_create_customer_and_project(client, make_org_user):
    u = make_org_user("developer")
    h = {"token": u["token"]}
    # 组内建客户
    c = client.post("/customers/", json={"name": "A公司", "industry": "制造"}, headers=h)
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    # 同用户在该客户下建项目（项目继承客户组）
    p = client.post("/projects/", json={"name": "A公司智能客服", "customer_id": cid}, headers=h)
    assert p.status_code == 200, p.text
    pj = p.json()
    assert pj["customer_id"] == cid
    assert pj["group_id"] == u["group_id"]


def test_unauthenticated_rejected(client):
    r = client.get("/customers/")
    assert r.status_code == 401
