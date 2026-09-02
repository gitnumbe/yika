"""P1.6 事件总线（S6）测试：schema + topic 路由 + 幂等。

覆盖：
- 事件 schema 含 {type, entity, entity_id, actor, at}
- topic 路由前缀订阅（requirement.delivered 触发 requirement.* 订阅者）
- at-least-once 幂等：同一事件重复投递只生效一次
- 未匹配路由的事件不被消费
"""
from app.platform.services.event_bus import (
    Event, EventDispatcher, InMemoryBackend, InMemoryIdempotencyStore)


def test_event_schema_fields():
    e = Event(type="requirement.delivered", entity="requirement", entity_id=12, actor="dev1")
    assert e.type == "requirement.delivered"
    assert e.entity == "requirement"
    assert e.entity_id == 12
    assert e.actor == "dev1"
    assert e.at  # 时间戳存在
    assert e.idempotency_key == "requirement.delivered:requirement:12"


def test_topic_routing_prefix_match():
    d = EventDispatcher(backend=InMemoryBackend(), idempotency_store=InMemoryIdempotencyStore())
    seen = []
    d.subscribe("requirement.", lambda ev: seen.append(ev.type))
    d.dispatch(Event(type="requirement.delivered", entity="requirement", entity_id=1))
    assert "requirement.delivered" in seen


def test_idempotency_dedupe():
    d = EventDispatcher(backend=InMemoryBackend(), idempotency_store=InMemoryIdempotencyStore())
    seen = []
    d.subscribe("req.", lambda ev: seen.append(ev.type))
    ev = Event(type="req.delivered", entity="requirement", entity_id=5)
    d.dispatch(ev)
    d.dispatch(ev)  # 重复投递（at-least-once）
    d.dispatch(ev)
    assert len(seen) == 1  # 幂等：只生效一次


def test_unmatched_routing_not_consumed():
    d = EventDispatcher(backend=InMemoryBackend(), idempotency_store=InMemoryIdempotencyStore())
    seen = []
    d.subscribe("knowledge.", lambda ev: seen.append(ev.type))
    d.dispatch(Event(type="requirement.delivered", entity="requirement", entity_id=1))
    assert seen == []  # 未匹配知识前缀，不消费
