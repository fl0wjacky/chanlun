"""第三批 B13：拿现在的引擎（core/segment.build_segments）推 L79 两张字符画（第二章第 1 批题 4、5），看线段怎么划。
笔序列照 `docs/spec/第二章-线段.md` §十 的端点读数（Iris 读图、两人对过）。每两点之间一笔，hi/lo 取两端。
作者答案（L79:68-70）：题 4 三段，题 5 两段（第二段从 3 起向上，未完成）。"""
import sys
sys.path[:0] = [".", "tools"]
from core.segment import build_segments, check_segments

CASES = {
    "题4": [9, 5, 8, 4, 12, 5, 9, 7, 11, 4, 6, 1],
    "题5": [13, 4, 8, 3, 12, 4, 8, 6, 11, 7, 10],
    "题5(b) 端点9改5": [13, 4, 8, 3, 12, 4, 8, 6, 11, 5, 10],
}

def pens_of(ps):
    return [dict(i0=k, i1=k + 1, x0=k, x1=k + 1, p0=a, p1=b, hi=max(a, b), lo=min(a, b))
            for k, (a, b) in enumerate(zip(ps, ps[1:]))]

for name, ps in CASES.items():
    pens = pens_of(ps)
    segs = build_segments(pens)
    desc = ["%d→%d %s%s" % (s["i0"], s["i1"], s["dir"], "（未完成）" if s.get("live") else "") for s in segs]
    print(name, "：", len(segs), "段 ｜", "；".join(desc), "｜ 自检违规", len(check_segments(segs, pens, unmeasured=[])))
