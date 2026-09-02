"""需求提炼服务：候选需求（开发文档 §5.3 契约）。

生产级要求：
1. 仅 discussion 场景由调用方触发（本函数不判断场景）。
2. 每条候选必带 source_ref 溯源；confidence 0-1。
3. 失败降级返回空数组 + quality 标记，不抛异常；候选只进候选区（防幻觉铁律）。
"""
import json

from .llm import get_llm

PROMPT = """你是需求分析师。请从下面的沟通笔记中提取客户潜在需求，输出 JSON 数组：
[{{"title": "需求标题", "description": "需求描述", "source_ref": "笔记中的原文原句", "confidence": 0.0, "reason": "为什么提炼"}}]
只输出 JSON 数组，不要其他内容。

笔记：
{text}"""


def extract_candidates(note_text: str) -> dict:
    """返回 {candidates, quality}。candidates 只进候选区，绝不自入库。"""
    llm = get_llm()
    try:
        raw = llm.chat([{"role": "user", "content": PROMPT.format(text=note_text)}]).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(raw)
        if not isinstance(data, list):
            data = []
        candidates = []
        for x in data:
            title = str(x.get("title", "")).strip()
            if not title:
                continue  # 无标题的候选丢弃（防止无效条目）
            candidates.append({
                "title": title[:200],
                "description": str(x.get("description", ""))[:2000],
                "source_ref": str(x.get("source_ref", ""))[:500],
                "confidence": float(x.get("confidence", 0.0) or 0.0),
                "reason": str(x.get("reason", ""))[:500],
            })
        return {"candidates": candidates, "quality": {"degraded": False}}
    except Exception as e:  # noqa: BLE001
        return {"candidates": [], "quality": {"degraded": True, "note": f"{type(e).__name__}: {e}"}}
