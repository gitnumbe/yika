"""笔记整理服务：四块结构化（开发文档 §5.2 契约）。

生产级要求：
1. JSON 解析容错：LLM 输出格式不符 → 重试一次 → 仍失败返回降级结构 + quality 标记，不抛异常断链。
2. 字段校验：四块字段 100% 完整（缺省补空串/空数组）。
"""
import json

from .llm import get_llm

PROMPT = """你是会议记录整理助手。请把下面的转写文本整理成结构化笔记，严格输出 JSON：
{{
  "summary": "一句话摘要（≤50字）",
  "points": [{{"topic": "话题名", "detail": "要点"}}],
  "decisions": [{{"content": "达成的结论"}}],
  "todos": [{{"owner": "谁", "item": "做什么", "pending": true}}]
}}
不要输出 JSON 以外的内容。

转写文本：
{transcript}"""


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def generate_note(transcript: str) -> dict:
    """返回 {summary, points, decisions, todos, quality}。永不抛异常。"""
    llm = get_llm()
    data = None
    attempts = 0
    last_err = ""
    while attempts < 2 and data is None:
        attempts += 1
        try:
            raw = llm.chat([{"role": "user", "content": PROMPT.format(transcript=transcript)}])
            data = _parse_json(raw)
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            data = None

    if data is None:
        return {
            "summary": "",
            "points": [],
            "decisions": [],
            "todos": [],
            "quality": {"degraded": True, "note": last_err or "parse failed"},
        }

    points = data.get("points") or []
    if isinstance(points, str):  # LLM 偶发输出字符串
        points = [{"topic": "", "detail": points}]
    decisions = data.get("decisions") or []
    if isinstance(decisions, str):
        decisions = [{"content": decisions}]
    todos = data.get("todos") or []
    if isinstance(todos, str):
        todos = [{"owner": "", "item": todos, "pending": True}]

    return {
        "summary": str(data.get("summary", ""))[:200],
        "points": points,
        "decisions": decisions,
        "todos": todos,
        "quality": {"degraded": False},
    }
