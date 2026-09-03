"""答疑服务：关键词检索 + 回流（开发文档 §5.4 契约）。

A4 三重保险：
1. 未命中 → needs_human=true（转技术/人工）
2. 低置信(覆盖率<阈值) → 也转人
3. 命中带引用（source=命中的知识条目标题，可追溯到知识库条目）

v3：Knowledge 用 body 字段（非 content），只检索已发布(published)知识（审核中 draft 不用于答疑）。
"""
import re

from ...models import Knowledge

# 停用词：不参与匹配的中文虚词/代词
_STOPWORDS = set("的了是在有和就不人都一一个也这那要会能到说很吧吗啊呢哦嗯还是把被对于或与及")


def _tokenize(text: str) -> set[str]:
    """2-gram 分词（无 jieba 依赖，够用于检索）。"""
    t = re.sub(r"\s+", "", text)
    grams = {t[i : i + 2] for i in range(len(t) - 1)} if len(t) > 1 else set(t)
    return {g for g in grams if g and not all(c in _STOPWORDS for c in g)}


def _search_knowledge(db, question: str):
    q_grams = _tokenize(question)
    if not q_grams:
        return None, 0
    best, best_score = None, 0
    # 仅检索已发布知识（审核中 draft 不用于答疑）
    for k in db.query(Knowledge).filter(Knowledge.status == "published").all():
        k_grams = _tokenize(k.title + " " + k.body)
        if not k_grams:
            continue
        score = len(q_grams & k_grams) / len(q_grams)  # 覆盖率 0-1
        if score > best_score:
            best, best_score = k, score
    # 阈值：覆盖率 < 0.25 视为未命中（低置信转人）
    return (best, best_score) if best_score >= 0.25 else (None, best_score)


def answer(db, question: str) -> dict:
    hit, score = _search_knowledge(db, question)
    if hit:
        return {
            "answer": hit.body,
            "source": hit.title,          # 引用 = 命中的知识条目标题（可溯源）
            "source_id": hit.id,
            "confidence": round(score, 2),
            "needs_human": False,         # 高置信命中直接答
        }
    return {"answer": "", "source": "", "source_id": None, "confidence": 0.0, "needs_human": True}
