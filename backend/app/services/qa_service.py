from ..models import Knowledge


def _search_knowledge(db, question: str):
    # MVP 用关键词重叠做简单检索，后续可换向量检索
    words = set(question)
    best, best_score = None, 0
    for k in db.query(Knowledge).all():
        score = len(words & set(k.title + k.content))
        if score > best_score:
            best, best_score = k, score
    return best if best_score > 0 else None


def answer(db, question: str) -> dict:
    hit = _search_knowledge(db, question)
    if hit:
        return {"answer": hit.content, "source": hit.title, "needs_human": False}
    return {"answer": "", "source": "", "needs_human": True}
