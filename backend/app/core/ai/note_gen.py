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


def completeness(note_data: dict) -> dict:
    """A6 四块完整性度量（P6.3 底线：完整度 ≥80%）。

    四块 = summary / points / decisions / todos。
    每块评分规则（满分 100）：
      summary:   非空 40 分
      points:    ≥1 条 25 分，每条有 topic+detail 再加 5 分（上限 25 分内浮动）
      decisions: ≥1 条 20 分，每条有 content 再加 5 分
      todos:     ≥1 条 15 分，每条有 owner+item 再加 5 分
    总分 = 四块得分之和，封顶 100。缺失留空字段不强行生成，如实计 0 分。
    """
    score = min(100, _raw_score(note_data))
    return {
        "score": score,             # 0-100
        "blocks_present": _blocks_present(note_data),  # 非空块数（0-4）
        "blocks": _block_flags(note_data),             # 每块是否非空
        "pass": score >= 80,        # ≥80 视为完整
    }


def _raw_score(note_data: dict) -> int:
    """四块原始分（bonus 可能使满分 >100，由外层 cap 到 100）。"""
    score = 0
    if (note_data.get("summary") or "").strip():
        score += 40

    points = note_data.get("points") or []
    if points:
        score += 25
        if all(isinstance(p, dict) and p.get("topic") and p.get("detail") for p in points):
            score += 5

    decisions = note_data.get("decisions") or []
    if decisions:
        score += 20
        if all(isinstance(d, dict) and d.get("content") for d in decisions):
            score += 5

    todos = note_data.get("todos") or []
    if todos:
        score += 15
        if all(isinstance(t, dict) and t.get("owner") and t.get("item") for t in todos):
            score += 5
    return score


def _block_flags(note_data: dict) -> dict:
    return {
        "summary": bool((note_data.get("summary") or "").strip()),
        "points": bool(note_data.get("points") or []),
        "decisions": bool(note_data.get("decisions") or []),
        "todos": bool(note_data.get("todos") or []),
    }


def _blocks_present(note_data: dict) -> int:
    return sum(1 for v in _block_flags(note_data).values() if v)


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
