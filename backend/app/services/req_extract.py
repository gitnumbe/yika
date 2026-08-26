import json

from .llm import get_llm

PROMPT = """你是需求分析师。请从下面的沟通笔记中提取客户潜在需求，输出 JSON 数组，每条包含 title(需求标题)、description(需求描述)、source_ref(引用原文原句，用于溯源)。只输出 JSON 数组，不要其他内容。\n\n笔记：\n{text}"""


def extract_candidates(note_text: str) -> list[dict]:
    llm = get_llm()
    raw = llm.chat([{"role": "user", "content": PROMPT.format(text=note_text)}]).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    return [{"title": x.get("title", ""), "description": x.get("description", ""), "source_ref": x.get("source_ref", "")} for x in data]
