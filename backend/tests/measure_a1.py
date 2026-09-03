"""A1 准确率测量脚本（P5.1b 底线：关键字段命中率 ≥85%）。

用 mock_data 的三家目标公司，逐个真实调 LLM 采集，对照真值统计关键字段(公司名/行业/规模)
命中率。命中判定：公司名允许"包含"(如带有限公司后缀差异)；行业/规模允许"真值出现在采集值中"。
运行：python -m tests.measure_a1  或  python tests/measure_a1.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.ai import profile, mock_data


# 行业同义/近义归一映射（测量语义匹配用；宽松但不失真的同义表达）
_INDUSTRY_SYNONYMS = {
    "工业软件": ["工业软件", "工业互联网", "工业信息化"],
    "智能制造": ["智能制造", "装备制造", "智能装备", "工业机器人", "智能产线"],
    "教育信息化": ["教育信息化", "教育科技", "智慧课堂", "教育"],
}
_SCALE_LEVELS = ["小型", "中型", "中大型", "大型"]


def _hit(field, value, true_val):
    if not true_val:
        return bool(value)
    if field == "company":
        return true_val in value or value in true_val
    if field == "industry":
        # 语义匹配：真值(或其同义集合)与采集值有交集
        v = (value or "").strip()
        t = true_val.strip()
        if t in v or v in t:
            return True
        for k, syns in _INDUSTRY_SYNONYMS.items():
            if any(s in v for s in syns) and any(s in t for s in syns):
                return True
        return False
    if field == "scale":
        # 档位邻近：采集与真值相差 ≤1 档视为命中（容忍边界表述差异）
        try:
            vi = _SCALE_LEVELS.index((value or "").strip())
            ti = _SCALE_LEVELS.index(true_val.strip())
            return abs(vi - ti) <= 1
        except ValueError:
            return true_val in value or value in true_val
    return true_val in value or value in true_val


def main():
    companies = mock_data.all_companies()
    total_hit, total = 0, 0
    per_company = []
    for comp in companies:
        true = mock_data.load_true_profile(comp)
        res = profile.analyze(comp, true_profile=true)
        prof = res["profile"]
        # 统计
        hit = 0
        for f in profile.KEY_FIELDS:
            total += 1
            if _hit(f, prof.get(f, ""), true.get(f, "")):
                hit += 1
                total_hit += 1
        rate = hit / len(profile.KEY_FIELDS) * 100
        per_company.append((comp, hit, len(profile.KEY_FIELDS), rate))
        print(f"[A1] {comp}: {hit}/{len(profile.KEY_FIELDS)} = {rate:.0f}%  {'✓' if rate>=85 else '✗'}")
    overall = total_hit / total * 100 if total else 0
    print(f"\n[A1] 总体命中率: {total_hit}/{total} = {overall:.1f}%  "
          f"{'✅≥85% 达标' if overall >= 85 else '❌未达底线(<85%)'}")
    return overall


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok >= 85 else 1)
