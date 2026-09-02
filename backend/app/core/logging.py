"""P0.5 日志骨架 —— 统一 logging 配置。

- 基础配置：根 logger + uvicorn/app logger，格式含时间/级别/logger/消息。
- 级别可经 .env 的 LOG_LEVEL 覆盖（默认 INFO）。
- 供 app 各模块 `logging.getLogger(__name__)` 使用；关键操作写 AuditLog（数据层），
  运行诊断用本 logging（文本层）。
"""
import logging
import sys

from ..config import settings


def setup_logging() -> None:
    """配置根 logger。幂等（重复调用安全）。"""
    level = getattr(settings, "log_level", None) or "INFO"
    numeric = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    if root.handlers:  # 已配置，避免重复追加
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.setLevel(numeric)
    root.addHandler(handler)

    # 降噪第三方库（可选）
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """业务模块统一取 logger 的入口。"""
    return logging.getLogger(name)
