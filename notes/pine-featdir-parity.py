# -*- coding: utf-8 -*-
"""把 `tradingview/chanlun.pine` 的 `featStd()` **逐行抄成 Python**，两种模式各跟引擎对账（只读）。

为什么要有这个：Pine 在这台机器上**编译不了、跑不了**；`tools/pine_lockstep.py` 只回答
「引擎自 pine 上次改动以来变了没有」，**不回答「pine 抄的和引擎算的是不是一回事」**。
本轮给特征序列的合并方向加了开关（小栋 ⑤ / card-205e04ea-302），pine 与引擎各有一份 —— 这个脚本量它们对不对得上。

    pine: featStd(eh, el, up, modeB)          ⟷  engine: core/segment.py::_feature_std(elems, up, mode)

**做法（两半，缺一不可）**：
  ① **抄写指纹**：从 pine 源码里把 featStd 那几行抠出来，与下面这份「逐行翻译表」的期望文本逐字比。
     有**同一行**、**同一分支顺序**的断言 ⇒ 谁改了 pine 而没改这里，脚本立刻红。
     （不证 pine 语法能编译 —— 那要 TradingView；这条限制是本脚本的边界，写在报告里。）
  ② **行为对账**：真实数据上跑出来的**每一条特征序列**（A/B 两次构建过程中被喂进 _feature_std 的全部输入，
     去重后）＋ 随机序列，两边逐条比 (h,l) 结果。

    python3 notes/pine-featdir-parity.py
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core                                   # noqa: E402
import core.segment as S                      # noqa: E402

PINE = os.path.join(ROOT, "tradingview", "chanlun.pine")

# 卡面点名的六份（与 notes/pine-p3-parity.py 同一组，便于并读）
FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]

# ─────────────────── ① 抄写指纹：pine 里必须有这些行（一字不差） ───────────────────
EXPECT_LINES = [
    "featStd(array<float> eh, array<float> el, bool up, bool modeB) =>",
    "goUp = modeB ? up : (m < 2 ? up : ah > mh.get(m - 2))",
    "mh.set(m - 1, goUp ? math.max(ah, h) : math.min(ah, h))",
    "ml.set(m - 1, goUp ? math.max(al, l) : math.min(al, l))",
    "[mh, ml] = featStd(eh, el, not segUp, featModeB)",
    "[mh, ml] = featStd(eh, el, up, featModeB)",
    'featModeB = featDir == "B 全程按线段方向"',
]


def norm(s):
    return " ".join(s.split())


def check_transcription():
    src = open(PINE, encoding="utf-8").read().split("\n")
    flat = [norm(x) for x in src]
    bad = []
    for want in EXPECT_LINES:
        n = flat.count(norm(want))
        if n != 1:
            bad.append((want, n))
    if bad:
        print("① 抄写指纹 ✗ —— pine 里这些行不是「恰好一次」：")
        for w, n in bad:
            print("   命中 %d 次：%s" % (n, w))
        return 1, None
    ln = {norm(x): i + 1 for i, x in enumerate(src)}
    print("① 抄写指纹 ✓ —— %d 行锚点各命中一次，行号如下：" % len(EXPECT_LINES))
    for w in EXPECT_LINES:
        print("   pine:%-5d %s" % (ln[norm(w)], w))
    return 0, src


# ─────────────────── ② pine 的逐行翻译（只读，不参与引擎） ───────────────────

def contains(ah, al, bh, bl):        # pine:135 contains()
    return (ah >= bh and al <= bl) or (bh >= ah and bl <= al)


def pine_feat_std(eh, el, up, modeB):
    """pine:featStd() 的逐行翻译 —— 变量名、分支顺序、赋值位置都对齐。"""
    mh, ml = [], []
    t = 0
    while t < len(eh):
        h, l = eh[t], el[t]
        m = len(mh)
        if m > 0 and contains(mh[m - 1], ml[m - 1], h, l):
            ah, al = mh[m - 1], ml[m - 1]
            goUp = up if modeB else (up if m < 2 else ah > mh[m - 2])
            mh[m - 1] = max(ah, h) if goUp else min(ah, h)
            ml[m - 1] = max(al, l) if goUp else min(al, l)
        else:
            mh.append(h), ml.append(l)
        t += 1
    return mh, ml


def load(name):
    import json
    b = json.load(open(os.path.join(ROOT, "data", name), encoding="utf-8"))
    return b.get("bars") or b.get("klines") or b if isinstance(b, dict) else b


def collect_inputs():
    """把真实数据构建过程中**喂进 _feature_std 的每一条输入**收集起来（A、B 各跑一遍）。"""
    seen, order = set(), []
    real = S._feature_std
    box = []

    def spy(elems, up, mode=S.FEAT_STD_DEFAULT):
        box.append(([dict(e) for e in elems], up))
        return real(elems, up, mode)

    S._feature_std = spy
    n_files = 0
    for f in FILES:
        try:
            pens = core.analyze(load(f))["pens"]
        except Exception as e:
            print("   跳过 %s：%s" % (f, e))
            continue
        n_files += 1
        for mode in (S.FEAT_STD_A, S.FEAT_STD_B):
            S.build_segments(pens, mode=mode)
    S._feature_std = real
    for elems, up in box:
        key = (tuple((e["h"], e["l"]) for e in elems), up)
        if key not in seen:
            seen.add(key)
            order.append((elems, up))
    return order, n_files


def main():
    rc, _ = check_transcription()
    if rc:
        return rc

    inputs, n_files = collect_inputs()
    print("\n真实输入：%d 份数据 ｜ 去重后的特征序列 %d 条（A、B 两次构建里的全部调用）"
          % (n_files, len(inputs)))

    rnd = random.Random(20261002)
    synth = []
    for _ in range(20000):                       # 随机序列：特意制造互相包含
        n = rnd.randint(0, 7)
        eh = [rnd.randint(0, 6) for _ in range(n)]
        el = [h - rnd.randint(0, 4) for h in eh]
        synth.append(([dict(h=eh[i], l=el[i], i=i) for i in range(n)], rnd.random() < 0.5))
    print("合成输入：%d 条随机特征序列（含大量互相包含）\n" % len(synth))

    for mode, modeB in ((S.FEAT_STD_A, False), (S.FEAT_STD_B, True)):
        bad = []
        n = 0
        for elems, up in inputs + synth:
            n += 1
            eng = S._feature_std([dict(e) for e in elems], up, mode)
            got = pine_feat_std([e["h"] for e in elems], [e["l"] for e in elems], up, modeB)
            want = ([(e["h"]) for e in eng], [(e["l"]) for e in eng])
            if got != want:
                bad.append((mode, up, ([(e["h"], e["l"]) for e in elems]), got, want))
        tag = "A（modeB=false）" if mode == S.FEAT_STD_A else "B（modeB=true）"
        print("模式 %s：比了 %d 条，不同 %d 条 %s" % (tag, n, len(bad), "✓" if not bad else "✗"))
        for b in bad[:3]:
            print("   ★ up=%s 输入=%s\n     pine→%s\n     引擎→%s" % (b[1], b[2], b[3], b[4]))

    # 开关本身要有阳性对照：两支真的会算出不同结果
    diff = sum(1 for elems, up in inputs + synth
               if pine_feat_std([e["h"] for e in elems], [e["l"] for e in elems], up, False)
               != pine_feat_std([e["h"] for e in elems], [e["l"] for e in elems], up, True))
    print("\n阳性对照：pine 两支算出不同结果的有 %d/%d 条 %s"
          % (diff, len(inputs + synth), "✓ 开关确实分叉" if diff else "✗ 两支一样 ⇒ 开关没接上"))
    print("\n★ 边界：本脚本证的是**抄写一致**（pine 源码那几行 ⟷ 引擎那份），"
          "**不证** pine 语法能在 TradingView 编译通过 —— 那要真环境。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
