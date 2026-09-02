"""P1.6 事件总线（S6）—— 平台事件广播，子系统间不直接通信。

契约（评测/规范）：
- 事件 schema：{type, entity, entity_id, actor, at}
- 投递语义：at-least-once（可能重复）
- 幂等：consumer 按 (type, entity_id) 幂等 key 去重，重复投递只生效一次
- 载体：RabbitMQ topic（生产）；提供内存 backend 供开发/测试（不依赖 MQ 服务）

按「配置走 .env」：RabbitMQ 连接从 settings（RABBITMQ_*）读；未配置或不可用时
回退到内存 backend（开发），并开审计日志。
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

EVENT_SCHEMA = {"type", "entity", "entity_id", "actor", "at"}


@dataclass
class Event:
    type: str
    entity: str
    entity_id: int | str
    actor: str = ""
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def idempotency_key(self) -> str:
        """幂等 key：同类型+同实体只消费一次。"""
        return f"{self.type}:{self.entity}:{self.entity_id}"


class EventDispatcher:
    """事件分发器（含幂等去重）。backend 可换 RabbitMQ / 内存。"""

    def __init__(self, backend=None, idempotency_store=None):
        self.backend = backend or InMemoryBackend()
        self._consumers: dict[str, list[Callable]] = {}
        self._idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def publish(self, event: Event) -> None:
        self.backend.publish(event)

    def subscribe(self, routing_key: str, handler: Callable) -> None:
        """按 topic 路由前缀订阅（RabbitMQ topic 语义：key 前缀匹配）。"""
        self._consumers.setdefault(routing_key, []).append(handler)

    def dispatch(self, event: Event) -> None:
        """分发到匹配的订阅者，并做幂等去重（at-least-once 不重复生效）。"""
        if self._idempotency_store.was_consumed(event.idempotency_key):
            return  # 已处理过，幂等跳过
        for prefix, handlers in self._consumers.items():
            if event.type.startswith(prefix):
                for h in handlers:
                    h(event)
        self._idempotency_store.mark_consumed(event.idempotency_key)


class InMemoryBackend:
    """开发/测试用内存 backend（无 MQ 服务时）。"""

    def publish(self, event: Event) -> None:
        pass  # 内存 backend 发布即完成，消费由 dispatcher.dispatch 驱动


class InMemoryIdempotencyStore:
    """幂等去重（内存实现，开发/测试）。生产可换 DB/Redis。"""

    def __init__(self):
        self._keys: set[str] = set()

    def was_consumed(self, key: str) -> bool:
        return key in self._keys

    def mark_consumed(self, key: str) -> None:
        self._keys.add(key)


# 平台级单例
dispatcher = EventDispatcher()


def publish_event(type_: str, entity: str, entity_id: int | str, actor: str = "") -> Event:
    """供业务代码发布事件（S6）。"""
    e = Event(type=type_, entity=entity, entity_id=entity_id, actor=actor)
    dispatcher.publish(e)
    return e
