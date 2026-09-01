"""去噪服务：小模型句子级二分类（决策 04）。

生产级要求：
1. 失败降级：小模型不可用时，用规则兜底（不阻塞流水线），返回 quality 标记。
2. 输出保留原始句序，只过滤 keep=False 的句子。
"""
import re

from .llm import get_denoise_llm

PROMPT = """你是会议记录去噪助手。下面是一段录音转写文本，已按句子分行。
请逐句判断是否保留：删除寒暄、重复、口水话、与主题无关的内容。
严格输出 JSON 数组：[{{"sentence": "原句", "keep": true/false, "reason": "保留/删除原因"}}]。
只输出 JSON，不要其他内容。

句子：
{lines}"""


# 规则兜底：口语化/寒暄/无信息量句式
_TRASH_PATTERNS = [
    r"^(嗯|哦|啊|诶|呃|额|对|好|行|可以|是|是的|那|然后|所以|就是说|这个|那个)[，。！？,\s]*$",
    r"^(哈哈|哈哈哈|呵呵|嘿嘿|笑)$",
    r"^(我给你说|你知道吗|是吧|对不对|是不是|我觉得吧|反正就是|怎么说呢|那个什么)$",
    r"^\s*[，。！？,.、\s]*\s*$",
]


def denoise_transcript(transcript: str) -> dict:
    """返回 {text, quality}。text 为去噪后文本，quality 标记降级来源。

    生产契约（开发文档 §5.5 简化版）：LLM 失败 → 规则兜底 → quality.rules_fallback=true
    """
    lines = [l for l in re.split(r"\n|(?<=[。！？])", transcript) if l.strip()]
    if not lines:
        return {"text": "", "quality": {"rules_fallback": False, "note": "empty transcript"}}

    try:
        llm = get_denoise_llm()
        raw = llm.chat([{"role": "user", "content": PROMPT.format(lines="\n".join(lines))}]).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        import json
        judgments = json.loads(raw)
        keep_lines = [j["sentence"] for j in judgments if j.get("keep")]
        return {"text": "\n".join(keep_lines), "quality": {"rules_fallback": False}}
    except Exception as e:  # noqa: BLE001 —— LLM 失败/JSON 解析失败 → 规则兜底
        keep_lines = [l for l in lines if not any(re.match(p, l) for p in _TRASH_PATTERNS)]
        return {
            "text": "\n".join(keep_lines),
            "quality": {"rules_fallback": True, "note": f"denoise_llm failed: {type(e).__name__}"},
        }
