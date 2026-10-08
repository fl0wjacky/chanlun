#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""J19：相邻周期的笔状态联动（级别联动.md 七 J19 续，L91、L93；Nova 10-08 11:34 定口径）。**只报警，不改图。**

    python3 tools/j19_check.py              # 印每一对的判定；rc 恒为 0（只报警）
    python3 tools/j19_check.py --self-test  # 反向臂：小周期上下翻转 ⇒ 违反率必须明显上去；上不去 ⇒ rc=1
    加 --full 跑全部三对（15m 那两对一趟约 4 分钟）；不加只跑 1h 对 4h 那一对（13 秒）

每个周期的当下状态 (d, s)（L91 的四种）——『编者口径』（Bram 11:35 提，按 analyze() 现成的笔和分型写）：
  - d：正在走的那一笔的方向 ＝ 最后一笔**已确认**笔的反方向（最后一笔向下 ⇒ d＝1）。
  - s＝0「出现分型构造」：最后一笔终点之后，`fx` 里已有一个跟 d 相反类型的分型（d＝1 看顶分型），且它正落在终点之后的
    极值上（`fx` 只收三根标准 K 线都出来了的分型 ⇒ 分型已成立、笔还没确认）。
  - s＝1「延伸中」：终点之后还没有这样的分型，或者有、但价格已越过它创了新极值。
  - 一笔都还没有 ⇒ 状态未定（None），不参与比较。
  状态只按**这个周期自己的**笔和分型算，不借 J18 的走势分界（Atlas 11:33）。

比法（Nova 10-08 11:36–11:37 定，级别联动.md 七 J19『编者口径』）：同一份冻结 K 线按整点聚合出大周期（跟 J18 同一套 aggregate）；
大周期**逐根**算前缀状态，取状态**变了的那一根** b。按**先后**比：从大周期上一次变状态那一根收盘起、到 b 收盘为止，小周期**出现过**
要求的状态就算过（L91、L93 原文都是「出现」）。两级都只用到 b 收盘的数据（不看未来）。两条硬断言（H/L 对称）：
  ① 大周期在 b 从 (1,1) 变 (1,0)：这段时间里小周期出现过 (1,0) 或 (-1,1)。L91 的前提（变之前大小周期都是 (1,1)）不成立 ⇒
     「前提不成立」，单独记，不算违反；
  ② 大周期在 b 变成 (-1,1)：这段时间里小周期出现过 (-1,1)。
同一刻的写法（只看 b 那一刻小周期的状态）也实现了（mode="same"），只给对照：实测原样就有 19～53% 的违反，不用。
「绝大多数先出 (-1,1)」是概率说法，**只印统计数**（① 里小周期已是反向延伸的占比），不当断言；「过滤」那句不做。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
from core.analyze import analyze                              # noqa: E402
from config import tick_of                                    # noqa: E402
from j18_check import load, aggregate, M                      # noqa: E402
from core.kline import quantize, _contains                     # noqa: E402
from core.pen import build_pens                               # noqa: E402

PAIRS = [("zec15.json", 15 * M, 60 * M), ("zec15.json", 15 * M, 30 * M), ("zec_1h.json", 60 * M, 240 * M)]
# selfcheck／predeploy 只跑这一对（13 秒）；15m 那两对要逐根算 2 万根 15m 的状态，一趟约 4 分钟，--full 才跑
QUICK = [("zec_1h.json", 60 * M, 240 * M)]


def _state_of(m, fx):
    """由（标准化序列, 分型）给出当下状态 (d, s)；跟 state() 同一个定义，只是不重跑整套 analyze()。"""
    pens, _ = build_pens(fx, m, "old", 4)
    if not pens:
        return None
    p = pens[-1]
    d = 1 if p["p1"] < p["p0"] else -1
    after = [x for x in m if x["i"] > p["i1"]]
    if not after:
        return (d, 1)
    ext = max(x["h"] for x in after) if d == 1 else min(x["l"] for x in after)
    want = "top" if d == 1 else "bot"
    hit = [f for f in fx if f["i"] > p["i1"] and f["type"] == want and f["price"] == ext]
    return (d, 0 if hit else 1)


def _frac(m, k):
    a, b, c = m[k - 1], m[k], m[k + 1]
    if b["h"] > a["h"] and b["h"] > c["h"] and b["l"] > a["l"] and b["l"] > c["l"]:
        return dict(k=k, i=b["ih"], type="top", price=b["h"])
    if b["l"] < a["l"] and b["l"] < c["l"] and b["h"] < a["h"] and b["h"] < c["h"]:
        return dict(k=k, i=b["il"], type="bot", price=b["l"])
    return None


_SE = {}


def states_each(bars, fn):
    """带缓存的 _states_each：同一份 K 线（按首尾时间、根数、最高价和收盘价的校验和认 —— 不能用高低差：上下翻转后高低差一根不变，会撞键）只算一次 —— 两种比法、原样／翻转复用。"""
    key = (fn, len(bars), bars[0]["t"] if bars else None, bars[-1]["t"] if bars else None,
           round(sum(b["h"] for b in bars), 6), round(sum(b["c"] for b in bars), 6))
    if key not in _SE:
        _SE[key] = _states_each(bars, fn)
    return _SE[key]


def _states_each(bars, fn):
    """逐根前缀的状态 [状态(bars[:1]), 状态(bars[:2]), …]。
    标准化照 core/kline._standardize_span 逐根推（它本来就是单遍、只改最后一根或追加），分型只有最后那一个三连会变，
    其余冻结；每根只重跑 build_pens。跟逐根 analyze() 的 state() 逐个对过（见 --self-test 第一格）。"""
    q = quantize([dict(b) for b in bars], tick_of(fn))
    out, m, frozen, k0 = [], None, [], 1
    for n, bar in enumerate(q):
        bh, bl = bar["h"], bar["l"]
        if m is None:                                   # 还在找第一对不包含的相邻 K 线
            if n >= 1 and not _contains(q[n - 1]["h"], q[n - 1]["l"], bh, bl):
                m = [dict(h=q[n - 1]["h"], l=q[n - 1]["l"], i=n - 1, ih=n - 1, il=n - 1),
                     dict(h=bh, l=bl, i=n, ih=n, il=n)]
            else:
                out.append(None)
                continue
        elif True:
            p, p2 = m[-1], m[-2]
            up = p["h"] > p2["h"] or (p["h"] == p2["h"] and p["l"] > p2["l"])
            if _contains(p["h"], p["l"], bh, bl):
                if up:
                    m[-1] = dict(h=max(p["h"], bh), l=max(p["l"], bl), i=n,
                                 ih=n if bh > p["h"] else p["ih"], il=n if bl > p["l"] else p["il"])
                else:
                    m[-1] = dict(h=min(p["h"], bh), l=min(p["l"], bl), i=n,
                                 ih=n if bh < p["h"] else p["ih"], il=n if bl < p["l"] else p["il"])
            else:
                m.append(dict(h=bh, l=bl, i=n, ih=n, il=n))
        while k0 <= len(m) - 3:                        # m[k0+1] 已不是最后一根 ⇒ k0 处的分型定了
            f = _frac(m, k0)
            if f:
                frozen.append(f)
            k0 += 1
        tail = _frac(m, len(m) - 2) if len(m) >= 3 else None
        out.append(_state_of(m, frozen + ([tail] if tail else [])))
    return out


def state(bars, fn):
    """→ (d, s) 或 None。bars 是一段前缀（只用到当下）。"""
    r = analyze([dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars], tick=tick_of(fn))
    if not r["pens"]:
        return None
    p = r["pens"][-1]
    d = 1 if p["p1"] < p["p0"] else -1                       # 最后一笔向下 ⇒ 现在走的是向上那一笔
    after = [x for x in r["std"] if x["i"] > p["i1"]]
    if not after:
        return (d, 1)
    ext = max(x["h"] for x in after) if d == 1 else min(x["l"] for x in after)
    want = "top" if d == 1 else "bot"
    hit = [f for f in r["fx"] if f["i"] > p["i1"] and f["type"] == want and f["price"] == ext]
    return (d, 0 if hit else 1)


def check_pair(fn, fstep, bstep, small=None, mode="seen"):
    """→ [dict(kind, c, big_from, big_to, small, verdict)]。
    kind：「①」大周期 (d,1)→(d,0)；「②」大周期变成反向延伸 (−d,1)。
    mode：「seen」先后出现过（Nova 11:36 定的口径）——从大周期上一次变状态那一根收盘起、到这一根收盘为止，小周期**出现过**
          要求的状态就算过；「same」同一刻——只看这一根收盘那一刻小周期的状态（给翻转臂对照用）。
    verdict：「通过」「违反」「前提不成立」（① 只认 L91 的前提：变之前大周期 (d,1)、窗口起点小周期也是 (d,1)）「未定」。"""
    small = small if small is not None else load(fn)
    big = aggregate(_src(fn, small), bstep)
    if big and big[-1]["n"] * fstep < bstep:
        big = big[:-1]
    bs_ = states_each(big, fn)
    ss_ = states_each(small, fn)
    st_ = [b["t"] for b in small]
    import bisect

    def upto(t_end):                                 # 小周期收盘不晚于 t_end 的最后一根下标（+1）
        return bisect.bisect_right(st_, t_end - fstep)
    out, prev, w0 = [], None, 0
    for n in range(len(big)):
        st = bs_[n]
        if st is None:
            continue
        if prev is not None and st != prev:
            kind = None
            if st[0] == prev[0] and prev[1] == 1 and st[1] == 0:
                kind = "①"
            elif st[1] == 1 and st[0] != prev[0]:
                kind = "②"
            j1 = upto(big[n]["t"] + bstep)
            if kind:
                win = [x for x in ss_[w0:j1] if x is not None]
                now = ss_[j1 - 1] if j1 else None
                d = prev[0] if kind == "①" else st[0]
                need = {(d, 0), (-d, 1)} if kind == "①" else {(d, 1)}
                if now is None or not win:
                    verdict = "未定"
                elif kind == "①" and (ss_[w0 - 1] if w0 else None) != prev:
                    verdict = "前提不成立"
                elif mode == "same":
                    verdict = "通过" if now in need else "违反"
                else:
                    verdict = "通过" if any(x in need for x in win) else "违反"
                out.append(dict(kind=kind, c=n, big_from=prev, big_to=st, small=now, verdict=verdict))
            w0 = j1
        prev = st
    return out


_BIG_SRC = {}


def _src(fn, small):
    """大周期的来源：默认就是小周期那份 K 线；self-test 翻转小周期时，大周期仍用原样那份（_BIG_SRC 里登记）。"""
    return _BIG_SRC.get(fn, small)


def summarize(res):
    n = {k: sum(1 for r in res if r["verdict"] == k) for k in ("通过", "违反", "前提不成立", "未定")}
    one = [r for r in res if r["kind"] == "①" and r["small"] is not None]
    rev = sum(1 for r in one if r["small"][0] != r["big_from"][0])
    return n, (rev, len(one))


def main(quiet=False, pairs=QUICK):
    viol = 0
    for fn, fs, bs in pairs:
        res = check_pair(fn, fs, bs)
        n, (rev, n1) = summarize(res)
        viol += n["违反"]
        if not quiet:
            print("%s %s %dm 对 %dm：大周期状态变化 %d 次（① %d、② %d）—— 通过 %d ／ 违反 %d ／ 前提不成立 %d ／ 未定 %d ｜ 统计：① 时小周期已是反向延伸 %d／%d" % (
                "⚠" if n["违反"] else "✓", fn, fs // M, bs // M, len(res),
                sum(1 for r in res if r["kind"] == "①"), sum(1 for r in res if r["kind"] == "②"),
                n["通过"], n["违反"], n["前提不成立"], n["未定"], rev, n1))
            for r in res:
                if r["verdict"] == "违反":
                    print("    违反 %s 大周期 %s→%s（c=%d）⇒ 小周期 %s" % (r["kind"], r["big_from"], r["big_to"], r["c"], r["small"]))
    return viol


def self_test(pairs=QUICK):
    """反向臂：小周期 K 线整段**上下翻转**（大周期照原样）⇒ 违反率必须明显上去。
    判有牙：翻转后违反率 ≥ 20%，且 ≥ 原样违反率的 5 倍。（10-08 实测「先后出现过」：原样 1.7～3.8%，翻转 28～46%。
    同一刻的写法翻转后也报得出来，但原样就有 19～53% 的违反 ⇒ 不用，见 spec 级别联动.md 七 J19『编者口径』。）"""
    miss = armed = 0
    for fn, fs, bs in pairs:
        small = load(fn)
        top = max(b["h"] for b in small) + min(b["l"] for b in small)
        flipped = [dict(t=b["t"], o=top - b["o"], h=top - b["l"], l=top - b["h"], c=top - b["c"]) for b in small]
        _BIG_SRC[fn] = small
        try:
            ok_res = check_pair(fn, fs, bs)
            bad_res = check_pair(fn, fs, bs, small=flipped)
        finally:
            _BIG_SRC.pop(fn, None)
        rate = lambda R: (sum(1 for r in R if r["verdict"] == "违反"), sum(1 for r in R if r["verdict"] in ("通过", "违反")))
        (nb, jb), (no, jo) = rate(bad_res), rate(ok_res)
        if not jb or not jo:
            print("· %s %dm 对 %dm：判不出（跳过）" % (fn, fs // M, bs // M))
            continue
        armed += 1
        rb, ro = nb / jb, no / jo
        ok = rb >= 0.20 and rb >= 5 * ro
        miss += not ok
        print("%s %s %dm 对 %dm：小周期上下翻转 ⇒ 违反 %d／%d（%.0f%%），原样 %d／%d（%.1f%%）" % (
            "✓" if ok else "✗", fn, fs // M, bs // M, nb, jb, 100 * rb, no, jo, 100 * ro))
    if not armed:
        print("✗ 没有一对量得出来 ⇒ 反向臂空转")
    return 1 if miss or not armed else 0


if __name__ == "__main__":
    which = PAIRS if "--full" in sys.argv else QUICK
    if "--self-test" in sys.argv:
        sys.exit(self_test(which))
    main(pairs=which)
    sys.exit(0)
