"""A4 答疑引用有效率测量脚本（P5.3b 底线：命中回答引用有效 ≥90%）。

A4 三重保险：未命中转人 / 低置信转人 / 必须带引用。
测量：对 mock 问题逐个检索知识库，命中条目的 id 与真值 id 一致 → 引用有效。
引用有效率 = 引用有效的问题数 / 总命中问题数。

运行：python tests/measure_a4.py
"""
import sys, os, re
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
from app.core.ai import mock_data
from app.core.ai import qa_service  # noqa: E402

_tokenize = qa_service._tokenize
_search_knowledge = qa_service._search_knowledge


class _FakeDB:
    """包装 mock 知识库条目为可检索对象（含 id/status）。"""
    def __init__(self, items):
        self.items = items
    def query(self, model):
        return self
    def filter(self, cond):
        return self
    def all(self):
        # 包装为带 .title/.body/.status 的简单对象
        class _K:
            def __init__(self, d):
                self.id = d["id"]; self.title = d["title"]; self.body = d["body"]; self.status = "published"
        return [_K(d) for d in self.items]


def main():
    items = mock_data.load_knowledge_items()
    db = _FakeDB(items)
    cases = mock_data.load_qa_cases()
    total, valid = 0, 0
    for q, true_id in cases.items():
        hit, score = _search_knowledge(db, q)
        if hit is None:
            print(f"[A4] '{q}': 未命中(转人) —— 不计入(未命中转人工)")
            continue
        total += 1
        ok = (hit.id == true_id)
        valid += 1 if ok else 0
        print(f"[A4] '{q}': 命中条目#{hit.id}「{hit.title}」 vs 真值#{true_id} "
              f"score={score:.2f} {'✓引用有效' if ok else '✗引用不符'}")
    rate = valid / total * 100 if total else 0
    print(f"\n[A4] 引用有效率: {valid}/{total} = {rate:.1f}%  "
          f"{'✅≥90% 达标' if rate >= 90 else '❌未达底线(<90%)'}")
    return rate


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok >= 90 else 1)
