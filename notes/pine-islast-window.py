#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""islast 画图：窗口内结构超过配额时，丢掉的是**最新**的还是**最老**的？

要回答的唯一问题：
    窗口内某类结构数量 > 该类配额时，留下的应该是**最新的那一批**。
    留最新 ⇒ 对（图上最新的结构永远在，右边不空）
    留最老 ⇒ 错（右边空着、左边满屏 —— 小栋看到的就是这张脸）

★ 它**证不了** pine。本仓没有 Pine 运行时（见 chanlun.pine 第 15~20 行那段警告）。
  它证的是：把 pine 里那段**选择规则**逐行抄成 Python 之后的性质。抄错了它照样绿 ——
  所以下面每条规则都标了对应的 pine 行号；改 pine 的人请对着改这里。

用法：
    python3 notes/pine-islast-window.py              # 全量：九份数据 × 四个窗口
    python3 notes/pine-islast-window.py --self-test  # 正臂自证：**用旧规则必须红**
退出码：
    0  全绿
    1  有违反（最新的结构被丢了）
    2  跑不动（数据缺 / 引擎抛异常）—— **查不了 ≠ 通过**
    3  --self-test 的正臂没红 ⇒ 这个检查本身不算数
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from core import analyze, signals                                     # noqa: E402

SKIP = ("annot", "mag", "sub")                                        # data/ 里不是K线序列的几份
WINDOWS = (1000, 3000, 6000, 9000)                                    # == input.int drawBars 的 minval/maxval 区间

# ── 新规则（chanlun.pine 当前值）。★ 改 pine 的配额必须同步改这里 ────────────────
PEN_LINE_CAP, SEG_LINE_CAP = 349, 150        # chanlun.pine `int PEN_LINE_CAP` / `int SEG_LINE_CAP`
PC_BOX_CAP, SC_BOX_CAP = 378, 120            # `int PC_BOX_CAP` / `int SC_BOX_CAP`
SIG_LB_CAP = 300                             # `int SIG_LB_CAP`

# ── 旧规则（改动前的 chanlun.pine，用于正臂）。这些数现在**已经不在 pine 里了** ──
OLD_PEN_CAP = 440            # 旧：`gLines.size() < 440`，笔先画
OLD_LINE_CAP = 499           # 旧：`gLines.size() < 499`，线段和笔**共用**这一个上限
OLD_PC_BOX_CAP = 480         # 旧：`gBoxes.size() < 480`，笔中枢先画
OLD_SC_BOX_CAP = 490         # 旧：`gBoxes.size() < 490`，段中枢和笔中枢**共用**
OLD_LB_CAP = 499             # 旧：`gLabels.size() < 499`


def n_up(z):
    """一个中枢在 drawCenter 里还会外挂几个高一级别框（每个占 1 格 box + 1 个标签）。
    == pine 的 `zdN(z)`：`showUp ? z.upZD.size() : 0`，showUp 默认 true。"""
    return len(z.get("up") or [])


# ── 正则序（旧）：最老 → 最新，满了就**跳过**继续往后（pine 用 `size() < cap` 当条件，不是 break）──
def select_old(items, cap, end, x0, used=0):
    kept = []
    for it in items:
        if end(it) < x0:
            continue
        if used + len(kept) >= cap:
            continue
        kept.append(it)
    return kept


# ── 倒序（新）：最新 → 最老，配额用完就 break（pine 里正是这么写的）──────────────
def select_new(items, cap, end, x0):
    kept = []
    for it in reversed(items):
        if end(it) < x0:
            continue
        if len(kept) >= cap:
            break
        kept.append(it)
    return kept


def load():
    d = os.path.join(ROOT, "data")
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or any(x in fn for x in SKIP):
            continue
        bars = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines")
        if not bars:
            continue
        out.append((fn, bars))
    return out


def windows_of(r, n, w):
    """复刻 pine 的窗口判据。每类结构"结束在哪根"的取法与 pine 逐处对齐：
       笔   : p.i1                              (pens)
       线段 : s.i1                              (segs)
       笔中枢: pens.get(z.PI1).i1               (pcs)
       段中枢: done.get(z.PI1).i1               (scs；done = 非 live 的 segs)
       买卖点: sig.bar                          (sigs)

    ★ 注意两个 PI1 不是一回事：pcs 的 PI1 是**笔下标**，scs 的 PI1 是**线段下标**。
      pine 里也是分开取的（pcs 用 pens.get，scs 用 done.get），这里照抄。
    """
    x0 = n - 1 - w
    pens, segs = r["pens"], r["segs"]
    # ★ 用 `.get("live")`：引擎**只给最后一条**（未完成的那条）加 `live=True`，其余根本**不带这个键**
    #   （实测 zec15 131 条、只有下标 130 带）。core/analyze.py:39 自己也是这么筛的 ——
    #   这里写成 `s["live"]` 会直接 KeyError，而不是筛出错误结果，算是不幸中的万幸。
    done = [s for s in segs if not s.get("live")]
    pcs = [z for z in r["centers"] if z["PI1"] < len(pens)]
    scs = [z for z in r["seg_centers"] if z["PI1"] < len(done)]
    return {
        "x0": x0, "pens": pens, "segs": segs, "pcs": pcs, "scs": scs,
        "e_pen": lambda p: p["i1"],
        "e_seg": lambda s: s["i1"],
        "e_pc": lambda z: pens[z["PI1"]]["i1"],
        "e_sc": lambda z: done[z["PI1"]]["i1"],
        "_done": done,
    }


def win(items, end, x0):
    return [it for it in items if end(it) >= x0]


def boxes(W, sc_mode="share"):
    """两类中枢的框怎么分。`sc_mode` 只有两种取值，专门为了让正臂能打到**同一个代码路径**上：

      "share"（正确，pine 现在的写法）：段中枢的天花板 = **笔中枢画完之后的真实占用 + SC_BOX_CAP**
                                        （对应 pine 里 `boxLimSC = gBoxes.size() + SC_BOX_CAP`
                                          写在**笔中枢循环之后** —— 位置本身就是修复内容）
      "abs"  （错的写法）：天花板 = 绝对值 SC_BOX_CAP。
              等价于把 `boxLimSC` 和 `boxLimPC` 并排写在两个循环**之前**：那时 clearAll 刚做完、
              gBoxes.size()==0 ⇒ 算出来就是 120。**我确实这么写过一版**，
              @nova-8980 逐行读出来的。

    ★ 这个函数存在的理由：先前 `run_new` 里 `gB` 跨两类共用、直接拿绝对值 `SC_BOX_CAP` 去比，
      **跟 pine 是同一个错** ⇒ 两个错互相印证，九份数据里又恰好没有"笔中枢超过 120 格"的情况
      （实测最坏 zec15@9000 是 82 格），于是**一直是绿的**。建模错了，尺子就跟着瞎。
    """
    x0 = W["x0"]
    gB = 0
    kept_pc = []
    for z in reversed(W["pcs"]):
        if W["e_pc"](z) < x0:
            continue
        if gB + 1 + n_up(z) > PC_BOX_CAP:
            break
        gB += 1 + n_up(z)
        kept_pc.append(z)
    lim = (gB + SC_BOX_CAP) if sc_mode == "share" else SC_BOX_CAP
    kept_sc = []
    for z in reversed(W["scs"]):
        if W["e_sc"](z) < x0:
            continue
        if gB + 1 + n_up(z) > lim:
            break
        gB += 1 + n_up(z)
        kept_sc.append(z)
    return kept_pc, kept_sc, gB


def run_new(W):
    """按**新规则**（倒序 + 各留配额）算出实际留下的东西。"""
    x0 = W["x0"]
    kept_pen = select_new(W["pens"], PEN_LINE_CAP, W["e_pen"], x0)
    kept_seg = select_new(W["segs"], SEG_LINE_CAP, W["e_seg"], x0)
    kept_pc, kept_sc, gB = boxes(W, "share")
    return {"pen": kept_pen, "seg": kept_seg, "pc": kept_pc, "sc": kept_sc, "boxes": gB}


def run_old(W):
    """按**旧规则**（正序 + 笔/线段共用、笔中枢/段中枢共用）算出留下的东西。正臂用。"""
    x0 = W["x0"]
    kept_pen = select_old(W["pens"], OLD_PEN_CAP, W["e_pen"], x0)
    kept_seg = select_old(W["segs"], OLD_LINE_CAP, W["e_seg"], x0, used=len(kept_pen))
    gB = 0
    kept_pc, kept_sc = [], []
    for z in W["pcs"]:
        if W["e_pc"](z) < x0:
            continue
        if gB >= OLD_PC_BOX_CAP:
            continue
        gB += 1 + n_up(z)
        kept_pc.append(z)
    for z in W["scs"]:
        if W["e_sc"](z) < x0:
            continue
        if gB >= OLD_SC_BOX_CAP:
            continue
        gB += 1 + n_up(z)
        kept_sc.append(z)
    return {"pen": kept_pen, "seg": kept_seg, "pc": kept_pc, "sc": kept_sc, "boxes": gB}


def newest_kept(kept, items, end, x0):
    """留下的里面，最新的那根 == 窗口里最新的那根？

    ★ 取 `max(end(it) for it in kept)`，**不要**写 `kept[0]`。
      写 `kept[0]` 是在悄悄假设"调用方按最新在前返回"—— 那测的就成了**列表顺序**，
      不是我们要问的**"最新的那根还在不在"**。负对照当场抓到这个：把顺序翻成正序、
      但配额大到 523 根全留下时，`kept[0]` 是**最老**那根 ⇒ 报"最新的不在"
      —— **553 根全在，却报违反**。假阳性比漏报还坏：它会让下一次有人真的把顺序写错时，
      分不清是"顺序错"还是"这根本来就该丢"。
    """
    w = win(items, end, x0)
    if not w:
        return True, 0, 0
    newest_k = max((end(it) for it in kept), default=None)
    return (newest_k == end(w[-1])), len(w), len(kept)


def self_test(data):
    """正臂：拿**旧规则**跑，两条都必须红。红了才说明这个检查接上了。"""
    ok = True
    print("== 正臂（旧规则，必须红）==")
    W = None
    for fn, bars in data:
        if fn != "zec15.json":
            continue
        r = analyze(bars)
        W = windows_of(r, len(bars), 9000)
        k = run_old(W)
        wp, ws = win(W["pens"], W["e_pen"], W["x0"]), win(W["segs"], W["e_seg"], W["x0"])
        alive, nw, nk = newest_kept(k["pen"], W["pens"], W["e_pen"], W["x0"])
        arm1 = (not alive) and len(wp) > OLD_PEN_CAP
        print("  臂① zec15@9000 笔 > %d 时最新的笔还在？  窗口 %d 笔，旧规则留 %d（最老的），"
              "最新那根%s  ⇒ %s"
              % (OLD_PEN_CAP, nw, nk, "在" if alive else "**不在**", "红 ✓" if arm1 else "★ 没红 ✗"))
        arm2 = len(k["seg"]) < len(ws)
        print("  臂② zec15@9000 线段一条不少？          窗口 %d 段，旧规则留 %d（被笔挤到 %d-%d=%d）"
              " ⇒ %s" % (len(ws), len(k["seg"]), OLD_LINE_CAP, OLD_PEN_CAP, OLD_LINE_CAP - OLD_PEN_CAP,
                         "红 ✓" if arm2 else "★ 没红 ✗"))
        if not arm1:
            print("     ★ 臂① 没红：要么这档撞不到 %d 笔，要么选择规则没接上。" % OLD_PEN_CAP)
        if not arm2:
            print("     ★ 臂② 没红：线段没被挤掉，这条臂在这份数据上不成立。")

        # ── 臂③ 段中枢不许被笔中枢挤掉 ──────────────────────────────────────────
        # ★ 真实九份数据**打不到**这一条：实测最坏（zec15@9000）笔中枢才占 82 格 < 119，
        #   所以旧的那版错法在这九份上照样绿 —— 这正是它能活到被 @nova-8980 逐行读出来的原因。
        #   要让它红，得**合成**一个"笔中枢多到占满"的窗口：把窗口里的 pcs 复制几份。
        #   复制的是中枢**条目**，每个条目仍指向真实的笔（PI1 不变）⇒ 判据本身没被改软。
        only_pc = dict(W, scs=[])
        base_used = boxes(only_pc, "share")[2]
        reps = 1
        while base_used * reps <= SC_BOX_CAP and base_used * (reps + 1) <= PC_BOX_CAP:
            reps += 1
        W2 = dict(W, pcs=W["pcs"] * reps)
        n_sc_in = len(win(W["scs"], W["e_sc"], W["x0"]))
        n_share = len(boxes(W2, "share")[1])
        n_abs = len(boxes(W2, "abs")[1])
        arm3 = (n_abs == 0) and (n_share == n_sc_in)
        print("  臂③ 段中枢份额：合成 %d 倍笔中枢（占 %d 格 > %d）后，窗口内 %d 个段中枢 —— "
              "份额写法留 %d，绝对值写法留 %d  ⇒ %s"
              % (reps, base_used * reps, SC_BOX_CAP, n_sc_in, n_share, n_abs,
                 "红 ✓" if arm3 else "★ 没红 ✗"))
        if not arm3:
            print("     ★ 臂③ 没红：份额写法没比绝对值写法多留下来 ⇒ 这条臂没打中那个错。")

        ok = arm1 and arm2 and arm3
    if W is None:
        print("   ★ 找不到 zec15.json ⇒ 正臂跑不了（exit=3）")
        return False
    return ok


def neg_control(data):
    """负对照：把**新规则**只翻方向、配额不动，检查必须变红；配额放到窗口装得下时，必须不红。

    这一条和 --self-test 问的不是同一件事：
      --self-test   ：旧规则（真的那个 bug）认不认得出来 —— 有没有"接上"。
      负对照        ：新规则这一路**判的是方向、不是列表顺序** —— 会不会假阳性。
    ★ 加这条是因为它当场抓到一个真错：`newest_kept` 原先取 `kept[0]`，等于偷偷假设
      "调用方按最新在前返回"；配额放大到 523 根全留下时它照样报违反（全在却说不全在）。
      假阳性比漏报更难发现 —— 屏幕上和真违反长得一样。这两条都得是绿的。
    """
    ok = True
    for fn, bars in data:
        if fn != "zec15.json":
            continue
        r = analyze(bars)
        W = windows_of(r, len(bars), 9000)
        pen = W["pens"]
        # ① 全留下 + 正序 ⇒ 最新的笔在，**不许**报违反
        a = select_old(pen, sum(1 for p in pen if W["e_pen"](p) >= W["x0"]) + 10, W["e_pen"], W["x0"])
        alive = newest_kept(a, pen, W["e_pen"], W["x0"])[0]
        print("  全留下 + 正序 ⇒ %s" % ("不误报 ✓" if alive else "★ 假阳性 ✗（全在却说不在）"))
        # ② 同一套配额、只翻方向 ⇒ 必须报违反
        b = select_old(pen, PEN_LINE_CAP, W["e_pen"], W["x0"])
        caught = not newest_kept(b, pen, W["e_pen"], W["x0"])[0]
        print("  同配额 + 正序 ⇒ %s" % ("抓到 ✓" if caught else "★ 瞎了 ✗（方向翻了还说绿）"))
        ok = ok and alive and caught
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--neg-control", action="store_true")
    a = ap.parse_args()

    data = load()
    if not data:
        print("★ data/ 里一份 K 线都没有 ⇒ 查不了（不是通过）")
        return 2

    if a.self_test:
        return 0 if self_test(data) else 3
    if a.neg_control:
        print("== 负对照（新规则这一路）==")
        return 0 if neg_control(data) else 3

    bad, binding = [], []
    print("%-18s %6s %6s  %-24s %s" % ("数据", "窗口", "窗口内笔", "留下的 笔/线段", "最新的那根还在？"))
    for fn, bars in data:
        try:
            r = analyze(bars)
        except Exception as e:                                        # noqa: BLE001
            print("★ %s 引擎跑不动 ⇒ 查不了（不是通过）：%s" % (fn, type(e).__name__))
            return 2
        n = len(bars)
        for w in WINDOWS:
            W = windows_of(r, n, w)
            k = run_new(W)
            npw = len(win(W["pens"], W["e_pen"], W["x0"]))
            nsw = len(win(W["segs"], W["e_seg"], W["x0"]))
            pen_ok, _, nk = newest_kept(k["pen"], W["pens"], W["e_pen"], W["x0"])
            seg_ok, _, nsk = newest_kept(k["seg"], W["segs"], W["e_seg"], W["x0"])
            pinch = npw > PEN_LINE_CAP or nsw > SEG_LINE_CAP
            if pinch:
                binding.append((fn, w, npw, nsw))
            tag = "" if (pen_ok and seg_ok) else "   ★★ 违反"
            if not (pen_ok and seg_ok):
                bad.append((fn, w, pen_ok, seg_ok))
            print("%-18s %6d %6d  %-24s 笔%s 段%s%s"
                  % (fn, w, npw, "%d / %d" % (nk, nsk),
                     "✓" if pen_ok else "✗", "✓" if seg_ok else "✗", tag))

    print()
    if binding:
        print("撞到配额的档（只有这些档真的在考选择规则）：")
        for fn, w, npw, nsw in binding:
            # ★ 别写成 `笔 523 (>349)` —— 那个写法让人以为**两个数都**超了，
            #   实际常常只有笔超。谁超谁没超分开标（这行被我自己写错过一次）。
            print("  %-18s @%-5d 笔 %-4d/%-4d %s   线段 %-4d/%-4d %s"
                  % (fn, w, npw, PEN_LINE_CAP, "★超" if npw > PEN_LINE_CAP else "   ",
                     nsw, SEG_LINE_CAP, "★超" if nsw > SEG_LINE_CAP else "   "))
    else:
        print("★ 没有一档撞到配额 ⇒ 这次全绿**没考到选择规则**，别当它证明了什么。")

    if bad:
        print()
        print("★ %d 处违反：最新的结构被丢了。" % len(bad))
        return 1
    print()
    print("✓ 所有档：窗口里最新的笔和线段都还在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
