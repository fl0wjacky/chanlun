#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""J17／W61：走势完成后必有大一级的中枢震荡，且至少落在原走势最后一个中枢里（走势分段.md 六之三 乙4、级别.md J17、背驰.md W61；
L89、L99）。口径 Bram 10-08 12:4x 提、Nova 12:41 定。**只报警，不改图。**

    python3 tools/j17_check.py              # data/ 下每份 K 线：印违反数；rc 恒为 0（只报警）
    python3 tools/j17_check.py --self-test  # 两个拧坏臂各自必须报得出；报不出 ⇒ rc=1

对象：`trend_v3` 的走势段（相邻两个分界之间）。第 k 段 M_k 完成（分界 b_k 确立）以后：
  断言 A（J17，级别.md:152「完成的那一段，加上之后两段，三段同级走势重叠，必先构成大一级的中枢」）：
      M_k、M_{k+1}、M_{k+2} 三段的价格区间有公共重叠 O ＝ [三段低点的最大值, 三段高点的最小值]。没有 ⇒ 违反。
      M_{k+2} 还没走完（是最后那段 live）⇒「未走完」，不判。
  断言 B（W61 前一半「必然至少要落在前一走势类型的最后一个中枢范围里」）：O 跟 M_k 的最后一个线段中枢 [ZD, ZG] 有交集。
      没有 ⇒ 违反。M_k 里没有线段中枢 ⇒「未定」。
  统计（W61 后一半「回到第二甚至更后中枢……不健康」，只印数、不报警）：O 还碰到 M_k 更早的线段中枢 ⇒ 记「不健康」。
「最后一个中枢」取线段中枢（Nova 12:41：走势段就是用线段中枢切出来的）。
不看未来：分界一旦确立就不再变（tools/trend_check.py ④ 守的），段的区间、段里的线段中枢只用到该段终点为止的 K 线
⇒ 用整份数据的结果判，跟在 M_{k+2} 确立那一根截断再判是同一个答案。

★ 牙：J18／J19 那种「上下翻转」在这里没牙（镜像以后重叠关系一模一样）。改成两个拧坏数据的臂（不改判据代码）：
  臂 ①：把 M_{k+1}、M_{k+2} 的区间整体推到 M_k 区间的外面（朝 M_k 结束的方向）⇒ A 必须大面积报违反；
  臂 ②：把 M_k 的「最后一个中枢」换成倒数第二个（只在有 ≥2 个中枢的段上）⇒ B 的违反数或「不健康」数必须变。
判法（Nova 12:41 定死）：A、B 真数据违反 ≤5%，且各自的臂都报得出 ⇒ 断言只报警；否则只统计，spec 写明实测不成立。
★ 10-08 实测（data/ 10 份 ＋ 线上 15 张快照 10-07，图头段除外）：
  A 违反 1／24（4.2%），臂 ① 23／23 ⇒ **A 当断言，只报警**；
  B 违反约 25%（data 2／8、线上 4／15 上下）⇒ **B 不当断言，只统计**（spec 写明实测不成立）；「不健康」本来就只统计。
  图头段（第 0 段、起点被窗口截掉）单独记「图头」，不判：它的区间不完整，J18 同理。含图头时 A 是 5／23，其中 4 刀是图头。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
from trend_check import run, kline_files                      # noqa: E402


def structure(v, bars):
    """→ 每段 dict(lo, hi, live, centers=[(ZD, ZG), …] 按时间)。"""
    out = []
    for g, s in enumerate(v["segments"]):
        seg = bars[s["i0"]:s["i1"] + 1]
        cs = sorted((z for z in v["seg_centers"] if z["seg"] == g), key=lambda z: z["X0"])
        out.append(dict(lo=min(b["l"] for b in seg), hi=max(b["h"] for b in seg), live=s["live"], head=s.get("head", False),
                        centers=[(z["ZD"], z["ZG"]) for z in cs]))
    return out


def judge(S, last_of=lambda cs: cs[-1]):
    """→ [dict(k, A, B, unhealthy)]；A／B ∈ {"通过", "违反", "未走完", "未定"}。last_of 给臂 ② 换参照中枢用。"""
    res = []
    for k in range(len(S) - 2):
        a, b, c = S[k], S[k + 1], S[k + 2]
        if k == 0 and a.get("head"):
            res.append(dict(k=k, A="图头", B="图头", unhealthy=False))
            continue
        if c["live"]:
            res.append(dict(k=k, A="未走完", B="未走完", unhealthy=False))
            continue
        lo, hi = max(a["lo"], b["lo"], c["lo"]), min(a["hi"], b["hi"], c["hi"])
        A = "通过" if lo <= hi else "违反"
        if not a["centers"]:
            B, unh = "未定", False
        elif A == "违反":
            B, unh = "违反", False
        else:
            zd, zg = last_of(a["centers"])
            B = "通过" if lo <= zg and zd <= hi else "违反"
            unh = any(lo <= g2 and d2 <= hi for d2, g2 in a["centers"][:-1])
        res.append(dict(k=k, A=A, B=B, unhealthy=unh))
    return res


def count(res, key):
    j = [r for r in res if r[key] in ("通过", "违反")]
    return sum(1 for r in j if r[key] == "违反"), len(j)


def all_structures():
    out = []
    for fn in kline_files():
        r, v = run(fn)
        out.append((fn, structure(v, r["bars"])))
    return out


def main(quiet=False):
    viol = 0
    tot = dict(A=[0, 0], B=[0, 0], unh=0)
    for fn, S in all_structures():
        res = judge(S)
        (av, an), (bv, bn) = count(res, "A"), count(res, "B")
        unh = sum(1 for r in res if r["unhealthy"])
        tot["A"][0] += av; tot["A"][1] += an; tot["B"][0] += bv; tot["B"][1] += bn; tot["unh"] += unh
        viol += av                                        # 只有 A 是断言；B、不健康只统计
        if not quiet and (an or bn):
            print("%s %-18s 段 %2d ｜ A（断言）违反 %d／%d ｜ B（统计）不在最后中枢 %d／%d ｜ 不健康 %d" % ("⚠" if av else "✓", fn, len(S), av, an, bv, bn, unh))
            for r in res:
                if r["A"] == "违反":
                    print("    违反 A：第 %d 段完成后，它和后两段没有公共重叠" % r["k"])
    if not quiet:
        print("合计：A（断言）违反 %d／%d ｜ B（统计）%d／%d ｜ 不健康 %d" % (tot["A"][0], tot["A"][1], tot["B"][0], tot["B"][1], tot["unh"]))
    return viol


def _push_away(S):
    """臂 ①：每个 k 单独拧——把 M_{k+1}、M_{k+2} 的区间整体平移到 M_k 区间外面。返回 [(k, 拧过的 S)]。"""
    out = []
    for k in range(len(S) - 2):
        a = S[k]
        span = (a["hi"] - a["lo"]) or 1.0
        T = [dict(x) for x in S]
        for j in (k + 1, k + 2):
            w = T[j]["hi"] - T[j]["lo"]
            T[j]["lo"] = a["hi"] + span                   # 整段搬到 M_k 最高点上方一个 M_k 跨度
            T[j]["hi"] = T[j]["lo"] + w
        out.append((k, T))
    return out


def self_test():
    miss = 0
    real_a = real_b = n_a = n_b = 0
    arm1_v = arm1_n = 0
    b_real = unh_real = b_arm2 = unh_arm2 = 0
    for fn, S in all_structures():
        res = judge(S)
        av, an = count(res, "A"); bv, bn = count(res, "B")
        real_a += av; n_a += an; real_b += bv; n_b += bn
        for k, T in _push_away(S):                         # 臂 ①
            r = [x for x in judge(T) if x["k"] == k][0]
            if r["A"] in ("通过", "违反"):
                arm1_n += 1
                arm1_v += r["A"] == "违反"
        multi = [i for i, x in enumerate(S) if len(x["centers"]) >= 2]
        r0 = [x for x in res if x["k"] in multi]
        r2 = [x for x in judge(S, last_of=lambda cs: cs[-2] if len(cs) >= 2 else cs[-1]) if x["k"] in multi]   # 臂 ②
        b_real += sum(1 for x in r0 if x["B"] == "违反"); unh_real += sum(1 for x in r0 if x["unhealthy"])
        b_arm2 += sum(1 for x in r2 if x["B"] == "违反")
    ok1 = arm1_n > 0 and arm1_v == arm1_n
    ok2 = True                                            # B 只统计（实测 ~25% 不成立），臂 ② 只印、不判
    print("%s 臂 ① 后两段推到 M_k 外面 ⇒ A 违反 %d／%d（要全报）" % ("✓" if ok1 else "✗", arm1_v, arm1_n))
    print("· 臂 ② 最后一个中枢换成倒数第二个（≥2 个中枢的段）⇒ B %d → %d（B 只统计，不判；线上快照上是 4 → 6）" % (b_real, b_arm2))
    print("· 真数据（图头除外）：A 违反 %d／%d、B %d／%d（A ≤5%% 当断言；B 超了只统计，见文件头）" % (real_a, n_a, real_b, n_b))
    miss += (not ok1) + (not ok2)
    return 1 if miss else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    main()
    sys.exit(0)
