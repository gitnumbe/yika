"""答疑服务：关键词检索 + 回流（开发文档 §5.4 契约）。

生产级改进：
1. 检索从"单字集合重叠"升级为"分词（2-gram）+ 权重评分"，避免单字噪声；
2. 未命中 → needs_human=true（转待答疑队列由前端 @技术人员）；
3. 支持预答（可选，二期）：未命中时用大模型生成预答候选（仍不落库）。
"""
import re

from ..models import Knowledge

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
    # 阈值：覆盖率 < 0.25 视为未命中
    return (best, best_score) if best_score >= 0.25 else (None, best_score)


def answer(db, question: str) -> dict:
    hit, score = _search_knowledge(db, question)
    if hit:
        return {
            "answer": hit.body,
            "source": hit.title,
            "confidence": round(score, 2),
            "needs_human": False,
        }
    return {"answer": "", "source": "", "confidence": 0.0, "needs_human": True}
