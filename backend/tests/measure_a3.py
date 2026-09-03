"""A3 需求提炼准确率测量脚本（P5.2b 底线：候选需求有效 ≥70%）。

对 mock 沟通记录逐个真实调 LLM 提炼候选需求，对照"真值有效需求"统计有效率。
有效率 = 提炼出的候选中被确认为有效(对上真值)的比例。
运行：python tests/measure_a3.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.ai import req_extract, mock_data


def _match(cand_title, true_reqs):
    """候选标题是否对上某个真值有效需求（模糊/词序无关匹配）。"""
    t = (cand_title or "").strip()
    if not t:
        return False
    # 去常见停用词后按关键词交集判断
    stop = "的一个功能支持与和及想要希望能做"
    def keysof(s):
        return set([c for c in s if c not in stop and not c.isspace()])
    tk = keysof(t)
    for tr in true_reqs:
        if tr in t or t in tr:
            return True
        # 词序无关：双方关键词交集占比
        rk = keysof(tr)
        if tk and rk and len(tk & rk) / len(rk) >= 0.6:
            return True
    return False


def main():
    notes = mock_data.all_notes()
    total_cands, valid_cands = 0, 0
    for key in notes:
        note = mock_data.load_note_text(key)
        true_reqs = mock_data.load_true_requirements(key)
        res = req_extract.extract_candidates(note)
        cands = res.get("candidates", [])
        valid = [c for c in cands if _match(c["title"], true_reqs)]
        rate = len(valid) / len(cands) * 100 if cands else 0
        total_cands += len(cands)
        valid_cands += len(valid)
        print(f"[A3] {key}: 候选{len(cands)} 有效{len(valid)} = {rate:.0f}%  {'✓' if rate>=70 else '✗'}")
        for c in cands:
            flag = "✓" if _match(c["title"], true_reqs) else "✗噪声"
            print(f"      - {c['title']} [{flag}]")
    rate = valid_cands / total_cands * 100 if total_cands else 0
    print(f"\n[A3] 总有效率: {valid_cands}/{total_cands} = {rate:.1f}%  "
          f"{'✅≥70% 达标' if rate >= 70 else '❌未达底线(<70%)'}")
    return rate


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok >= 70 else 1)
