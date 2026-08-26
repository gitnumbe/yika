import json

from .llm import get_llm

PROMPT = """你是会议记录整理助手。请把下面的转写文本整理成结构化笔记，严格输出 JSON，包含四个字段：summary(一句话摘要)、points(分段要点)、decisions(达成的决策)、todos(待办/疑问)。不要输出 JSON 以外的内容。\n\n转写文本：\n{transcript}"""


def generate_note(transcript: str) -> dict:
    llm = get_llm()
    raw = llm.chat([{"role": "user", "content": PROMPT.format(transcript=transcript)}])
    # 容错：剥离可能的 markdown 代码块包裹
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    return {
        "summary": data.get("summary", ""),
        "points": data.get("points", ""),
        "decisions": data.get("decisions", ""),
        "todos": data.get("todos", ""),
    }
