"""A1 客户画像采集（P5.1b）。

输入：目标公司名（用户只提供这个）。
流程：取数据源(开发用 mock_data 原始文本；生产接真实爬取) → LLM 整理成结构化档案
     → 自动校验(公司名/行业/规模 关键字段一致性、可信度) → 存疑字段标记"待人工确认"。
准确率底线（已定）：关键字段(公司名/行业/规模) 命中率 ≥ 85%。
兜底（已共识）：自动校验 + 存疑字段才推人工；信任字段直接入档；不搞全量人工卡审。
"""
import json

from .llm import get_llm
from . import mock_data

# 关键字段 = 准确率底线衡量对象（对照真值核对）
KEY_FIELDS = ["company", "industry", "scale"]

# 结构化提取 prompt（只输出 JSON 对象）
_PROMPT = """你是企业信息录入助手。从下面的官网/工商文本整理目标公司的结构化档案。

只输出一个 JSON 对象，不要其它任何文字，字段：
{{"company":"公司名(用用户给的目标名)","industry":"行业","scale":"规模(大型/中大型/中型/小型)","main_business":"主营业务","website":"官网(无则空)","background":"背景"}}

目标公司：{company}
数据源文本：
{sources}
"""


def build_profile(company: str, sources_text: str) -> dict:
    """调 LLM 从原始文本整理结构化公司档案。"""
    llm = get_llm()
    raw = llm.chat([{"role": "user", "content": _PROMPT.format(
        company=company, sources=sources_text)}]).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("A1 LLM 返回非对象")
    return data


def validate_profile(data: dict, true_profile: dict = None) -> dict:
    """自动校验 + 存疑字段推人工。

    - company 必须以目标公司名为准（用户给定，校验是否一致/含）
    - industry/scale 关键字段：与真值比对(测量时)或做非空+可信度判断
    - 返回 {field: {value, confidence, need_human}}
    - 存疑字段 need_human=True（不加 label 全量卡审，只对存疑字段）
    """
    result = {}
    for f in KEY_FIELDS:
        val = data.get(f, "")
        need_human = False
        confidence = 0.9
        if isinstance(val, str):
            val = val.strip()
        if not val:
            confidence = 0.0
            need_human = True  # 缺失 → 存疑，待人工
        # 真值比对（测量场景）：命中才高置信；否则降 + 推人工
        if true_profile and f in true_profile:
            t = true_profile[f]
            if f == "company":
                ok = t and (t in val or val in t)  # 允许包含（含"有限公司"后缀差异）
            else:
                ok = t and (val and (t in val or val in t))
            if not ok:
                confidence = 0.3
                need_human = True
        result[f] = {"value": val, "confidence": confidence, "need_human": need_human}
    return result


def analyze(company: str, sources_text: str = None, true_profile: dict = None) -> dict:
    """A1 完整流程：采集 + 校验，返回档案 + 存疑字段标记。"""
    raw = sources_text if sources_text is not None else mock_data.load_raw_source(company)
    data = build_profile(company, raw)
    validation = validate_profile(data, true_profile)
    return {"company": company, "profile": data, "validation": validation}
