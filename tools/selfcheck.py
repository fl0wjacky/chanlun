#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎自检：跑一遍全部不变量检查。任何一项不为 0 都说明引擎有问题。

K 线层（标准化 / 分型）→ 笔层（不变量 + 「笔内不能再切」独立复核 + 端点极值诊断）
→ 线段层（不变量 + 按原文定义独立复核）→ 中枢层（类中枢、线段中枢：终结方式按定义重验）
→ 扩展合成（区间只看前三段、有重叠必合、级别不乱添）。第 54 课算例另见 tools/verify_l54.py。
每个校验都做了变异测试：喂进故意做错的输入，确认它真能报错（见文件末尾）。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from config import data
from core import analyze, analyze_file, summarize, check_standardized, check_fractals_alternate
from core.pen import check_pens, nonextreme_pens, unsplit_violations, build_pens_v1
from core.segment import check_segments, verify_by_definition, nonextreme_endpoints
from core.center import check_centers
from core.extend import check_hierarchy
from core.signals import signals, check_signals, zero_axis, ZA_THRESHOLD

DATASETS = [("aaplusdt_4h.json", "AAPL 4h"), ("aaplusdt_2h.json", "AAPL 2h"),
            ("aaplusdt_1h.json", "AAPL 1h"), ("aaplusdt_30m.json", "AAPL 30m"),
            ("zec15.json", "ZEC 15m")]

FAIL = 0
SKIP = 0
R = {tag: analyze_file(fn) for fn, tag in DATASETS}


def count(label, n, note=""):
    """打印一项违规计数并计入总数。"""
    global FAIL
    FAIL += n
    print("  %-26s: %d  (应为 0)%s" % (label, n, note))


def skip(label, why):
    """第三态：**本格未执行** —— 夹具 / 前提没造出来，判据压根没跑。

    为什么既不能报 0 也不能报违规：报 0 是**假绿**（有东西没查，却说没事）；
    报违规是把「工具没在岗」折进「被测对象有罪」。两个都是在编数。
    所以给它自己的词、自己的计数、自己的非零退出码 —— **「工具在不在岗」必须自己喊，
    不能靠"没问题"的结论替它证明**（今晚在变异扫上撞的就是这个：夹具一没造出来，
    `next()` 抛裸 StopIteration，图上那一格被读成"判据抓住了"，其实判定根本没发生）。
    """
    global SKIP
    SKIP += 1
    print("  %-26s: 未执行  ← 判据没跑，别读成通过  （%s）" % (label, why))


def same_dir_starts(centers, pens, segs):
    """类中枢首笔必须与段反向（L64:31 / L64:35-36 下跌段里是上下上）—— 数有多少个中枢
    首笔仍是与段同向的（应为 0）。"""
    seg_dir = {}
    for s in segs:
        for k in range(s["PI0"], s["PI1"] + 1):
            seg_dir[k] = s["dir"]

    def pdir(p):
        return "up" if p["p1"] > p["p0"] else "down"

    return sum(1 for z in centers if pdir(pens[z["PI0"]]) == seg_dir.get(z["PI0"]))


def cross_seg_links(centers, big, segs):
    """类中枢之间的趋势/背驰/扩展合成限同一段内（小栋 10-03 定 A；L69:23 / L94:24 / L65:112 段内类背驰）——
    数两样跨段的东西（应都为 0）：① 前后两个类中枢不在同一段、rel 却不是『—』；② 合成体成员跨了段。
    段归属**从 segs 按 PI0 现算**，不读引擎自己打的 `seg` 字段（尺不读被测对象的自报）。"""
    owner = {}
    for si, s in enumerate(segs):
        for k in range(s["PI0"], s["PI1"] + 1):
            owner.setdefault(k, si)              # 段界那根笔两段共用：归前一段（类中枢 PI0 ≥ 段 PI0+1，碰不到）
    rel = sum(1 for k in range(1, len(centers))
              if owner.get(centers[k - 1]["PI0"]) != owner.get(centers[k]["PI0"]) and centers[k]["rel"] != "—")
    syn = sum(1 for b in big if len({owner.get(m["PI0"]) for m in b.get("members", [b])}) > 1)
    return rel, syn


for tag, r in R.items():
    m = r["std"]
    print("=" * 72)
    print("[%s] %s" % (tag, summarize(r)))
    # K 线层
    count("相邻仍含包含关系", len(check_standardized(m)))
    count("相邻高点相等", sum(1 for i in range(len(m) - 1) if m[i]["h"] == m[i + 1]["h"]))
    count("相邻低点相等", sum(1 for i in range(len(m) - 1) if m[i]["l"] == m[i + 1]["l"]))
    count("分型类型未严格交替", len(check_fractals_alternate(r["fx"])))
    # 分型：4 条件版 vs 只看高点 / 低点版，结果必须一致（「低点也最高」是自动的）
    only_h = {k for k in range(1, len(m) - 1) if m[k]["h"] > m[k - 1]["h"] and m[k]["h"] > m[k + 1]["h"]}
    only_l = {k for k in range(1, len(m) - 1) if m[k]["l"] < m[k - 1]["l"] and m[k]["l"] < m[k + 1]["l"]}
    tops = {f["k"] for f in r["fx"] if f["type"] == "top"}
    bots = {f["k"] for f in r["fx"] if f["type"] == "bot"}
    count("顶分型 4条件≠只看高点", len(tops ^ only_h))
    count("底分型 4条件≠只看低点", len(bots ^ only_l))
    # 笔层
    P, std = r["pens"], m
    count("笔不变量违规", len(check_pens(P, r["seq"], std, r["pen_rule"])))
    count("笔内还能再切出三笔", len(unsplit_violations(P, r["fx"], std, r["pen_rule"])),
          "　｜ 诊断：端点非极值 %d（剧烈扩张震荡，两道回头修正都救不回，只报数）" % len(nonextreme_pens(P, std)))
    # 线段层
    S, P = r["segs"], r["pens"]
    _um = []
    count("线段不变量违规", len(check_segments(S, P, _um)))
    if _um:                                      # 自检 A 取不到第一个反向线段：不退回宽版、不算过（Nova 10-06，同 ⑧ 口径）
        skip("线段自检 A（非极值起点 ① 型）", "%d 段取不到 X 之后第一个反向线段，例 %s" % (len(_um), _um[:2]))
    count("线段定义复核违规", len(verify_by_definition(S, P)),
          "　｜ 诊断：终点非段内极值 %d（原文未要求，只报数）" % len(nonextreme_endpoints(S)))
    # 中枢层
    count("类中枢不变量违规", len(check_centers(r["centers"], P, stops=[s["PI1"] + 1 for s in S])))
    count("类中枢起笔与段同向", same_dir_starts(r["centers"], P, S),
          "　← L64:31/L64:35-36 首笔必须反向（下跌段里是上下上）")
    count("类中枢扩展合成违规", len(check_hierarchy(r["big"], r["centers"], P)))
    _xr, _xs = cross_seg_links(r["centers"], r["big"], S)
    count("类中枢跨段 rel", _xr, "　← 段首 rel 必须是『—』（L69:23 / L94:24 段内类背驰）")
    count("类中枢跨段合成", _xs)
    count("买卖点复核违规", sum(len(check_signals(signals(r, lv, m), r, lv, m)) for lv in ("seg", "pen") for m in ("macd", "slope")))
    # 「B 段回抽 0 轴附近」那条必要条件 —— **默认不接进买卖点判定**（2026-09-30 拍板）。
    # 这里印的是**读数不是红**：口径（统计量 / 窗口 / 阈值）全是我们发明的数，原文只给"附近"两个字，
    # 样本又少 ⇒ 先把数摆在明面上（谁、几个、r 多少），别让它藏在一个默认关的开关后面没人看得见。
    _za = zero_axis(signals(r, "seg", "macd"), r, "seg") + zero_axis(signals(r, "pen", "macd"), r, "pen")
    _off = [x for x in _za if not x["ok"]]
    print("  %-26s: %d 个一买/一卖 · 没回抽（r > %.2f）%d 个%s" % (
        "[0 轴回抽] 读数（非违规）", len(_za), ZA_THRESHOLD, len(_off),
        "　← " + "、".join("%s @%d r=%.3f" % (x["kind"], x["bar"], x["r"]) for x in _off) if _off else ""))
    count("线段中枢不变量违规", len(check_centers(r["seg_centers"], [s for s in S if not s.get("live")])))

# ---- rust-chan 53 例（小栋 10-03 定 ③A）：上游线段划分例子逐个对，口径不同的必须带原文出处 ----
import rustchan_cases                                            # noqa: E402  （tools/ 已在 sys.path）
from core.segment import build_segments as _bs                   # noqa: E402
print("=" * 72)
_rc = rustchan_cases.load()["cases"]
print("[rust-chan 53 例] 逐位相同 %d · 口径不同（有原文出处）%d"
      % (sum(c["verdict"] == "identical" for c in _rc), sum(c["verdict"] == "caliber" for c in _rc)))
_rcb = rustchan_cases.check(_bs)
count("rust-chan 例子对不上", len(_rcb), ("　← " + " ｜ ".join(_rcb[:3])) if _rcb else "")
# 探针：两条必须红 —— ① 引擎把没走完的段也当已确认（live 全抹掉）；② 把一个「口径不同」的例子改标成「逐位相同」
_rp1 = rustchan_cases.check(lambda pens: [dict(x, live=False) for x in _bs(pens)])
_rc2 = [dict(c) for c in _rc]
_k = next(i for i, c in enumerate(_rc2) if c["verdict"] == "caliber")
_rc2[_k]["verdict"] = "identical"
_rp2 = rustchan_cases.check(_bs, _rc2)
count("rust-chan 探针（live 抹掉）没红", 0 if _rp1 else 1, "　｜ 抓到 %d 处" % len(_rp1))
count("rust-chan 探针（口径改标相同）没红", 0 if _rp2 else 1, "　｜ 抓到 %d 处" % len(_rp2))

# ---- 背驰力度的四种看法（docs/spec/背驰.md 第六节）：新看法 signals 与独立复核一致 + 两个探针必须红 ----
import sys as _sys                                               # noqa: E402
_S = _sys.modules["core.signals"]                                # core/__init__ 把 signals 导成了函数，模块要从这里拿
print("=" * 72)
_bvi = sum(len(_S.check_signals(_S.signals(r_, lv_, m_), r_, lv_, m_))
           for r_ in R.values() for lv_ in ("seg", "pen") for m_ in ("lines", "peak", "macd_or_lines"))
count("背驰新看法 signals≠独立复核", _bvi, "　← lines / peak / macd_or_lines 三种，两层")


def _probe(measure, patch_name, fake):
    """把 _S.<patch_name> 换成 fake 跑 measure：先看输出真变了没有（没变 ⇒ 探针空转，记「未执行」），
    变了就要求 check_signals 抓到 ≥1 处。"""
    base = {(t_, lv_): _S.signals(r_, lv_, measure) for t_, r_ in R.items() for lv_ in ("seg", "pen")}
    real = getattr(_S, patch_name)
    setattr(_S, patch_name, fake(real))
    try:
        moved = sum(_S.signals(r_, lv_, measure) != base[(t_, lv_)] for t_, r_ in R.items() for lv_ in ("seg", "pen"))
        caught = sum(len(_S.check_signals(_S.signals(r_, lv_, measure), r_, lv_, measure))
                     for r_ in R.values() for lv_ in ("seg", "pen"))
    finally:
        setattr(_S, patch_name, real)
    return moved, caught


def _rev_lines(real):
    def f(A, C, want_down, data, measure, ratio):
        if measure == "lines":
            c_, a_ = _S.lines_extreme(C, data), _S.lines_extreme(A, data)
            return all((x <= y) if want_down else (x >= y) for x, y in zip(c_, a_))   # 比较方向反过来
        return real(A, C, want_down, data, measure, ratio)
    return f


def _or_flip_lines(real):
    # 「或」里黄白线那半比较方向反了 ⇒ 多发出不该发的点，独立复核必须抓到。
    # 不用「或写成且」：那只会少发点，而这道门是单侧的（只核发出来的点合不合规，card-bbfd7719），少发抓不到。
    def f(A, C, want_down, data, measure, ratio):
        if measure == "macd_or_lines":
            return (real(A, C, want_down, data["macd"], "macd", ratio)
                    or real(A, C, not want_down, data["lines"], "lines", ratio))
        return real(A, C, want_down, data, measure, ratio)
    return f


def _mean_peak(real):
    def f(u, hist, measure="macd"):
        if measure == "peak":                                    # 峰值换成均值
            v = [h for h in hist[u["i0"]:u["i1"] + 1] if (h > 0 if u["p1"] > u["p0"] else h < 0)]
            return abs(sum(v) / len(v)) if v else 0
        return real(u, hist, measure)
    return f


for _name, _m, _pn, _fk in (("黄白线比较方向反过来", "lines", "_diverges", _rev_lines),
                            ("峰值换成均值", "peak", "strength", _mean_peak),
                            ("面积或黄白线里黄白线方向反了", "macd_or_lines", "_diverges", _or_flip_lines)):
    _mv, _ct = _probe(_m, _pn, _fk)
    if _mv == 0:
        skip("背驰探针（%s）没红" % _name, "这几份数据上变异没改动任何输出，探针空转")
    else:
        count("背驰探针（%s）没红" % _name, 0 if _ct else 1, "　｜ 改动 %d 组输出、抓到 %d 处" % (_mv, _ct))

# ---- 画笔的区间最值（core/pen.RangeExt）：直接跟切片 max/min 在所有 (k0, k1) 上比 ----
# 只比 build_pens 的输出证不了它对：Atlas 10-04 把右端点漏掉（hi = k1+size），9 份数据 × 两种笔照样 0 不同。
from core.pen import RangeExt, check_range_ext                   # noqa: E402


class _RangeExtNoRight(RangeExt):                                # 变异：区间漏掉右端点 k1
    def ext(self, k0, k1, top):
        k1 = min(k1, self.n - 1)
        if k0 < 0 or k0 > k1:
            raise ValueError
        return RangeExt.ext(self, k0, k1 - 1, top) if k1 > k0 else (
            self.tmax[k0 + self.size] if top else self.tmin[k0 + self.size])


print("=" * 72)
count("画笔区间最值 ≠ 切片", check_range_ext())
_rn = check_range_ext(_RangeExtNoRight)
count("区间最值探针（漏右端点）没红", 0 if _rn else 1, "　｜ 抓到 %d 处" % _rn)

# ---- 变异测试：校验器必须能抓住故意做错的输入 ----
print("=" * 72)
print("[变异测试] 校验器对故意做错的输入必须报错")
r = R["AAPL 30m"]
P1, _ = build_pens_v1(r["fx"])                                   # v1 划笔：约三成端点不是极值
caught = len(nonextreme_pens(P1, r["std"]))
count("v1 划笔的非极值端点未被发现", 0 if caught else 1, "　（抓到 %d 笔）" % caught)
seq = r["seq"]                                                   # 把连续三笔硬合成一笔
from core.pen import _pens_of
if len(seq) < 12:                                                # 变异可以把笔数削到凑不出夹具
    skip("硬合并的三笔未被发现", "seq 只有 %d 根，凑不出要合并的那三笔" % len(seq))
else:
    merged = seq[:10] + seq[12:]
    caught = len(unsplit_violations(_pens_of(merged), r["fx"], r["std"]))
    count("硬合并的三笔未被发现", 0 if caught else 1, "　（抓到 %d 笔）" % caught)
# 把一个端点挪到离前一端点只隔 2 根。**取中间那根，不写死第 5 根** —— 这句判据的意图是
# 「挪到只隔 2 根」，跟"第几根"无关；写死下标等于给夹具绑一个与被测对象无关的常数，
# 变异把 seq 变短就 IndexError，而这一格**本来根本不必未执行**（判据一次都不用丢）。
if len(seq) < 3:
    skip("隔得不够的笔未被发现", "seq 只有 %d 根，挪不动端点" % len(seq))
else:
    i = max(1, len(seq) // 2)
    bad_seq = seq[:i] + [dict(seq[i], k=seq[i - 1]["k"] + 2)] + seq[i + 1:]
    count("隔得不够的笔未被发现", 0 if check_pens(_pens_of(bad_seq), bad_seq, r["std"]) else 1)

# 线段：特征序列开头的包含若按 K 线的办法丢掉而不合并（v1 的毛病），独立复核必须报错。
# 上面 5 组数据恰好不受影响，这里用 12 标的 15 分钟里的 BNB（会改变端点）。
import core.segment as SG
from core.kline import standardize
rows = json.load(open(data("m15_sub.json"), encoding="utf-8"))["BNBUSDT"]
Pb = analyze([dict(t=i, o=o, h=h, l=l, c=c) for i, (_, o, h, l, c) in enumerate(rows)])["pens"]
# ★ 第三参数跟着 `_feature_std(elems, up, mode)` 走（默认值放最右，老调用点不用改）。
_good, SG._feature_std = SG._feature_std, lambda xs, up, mode=None: [dict(x, ih=x["i"], il=x["i"]) for x in standardize(xs)]
caught = len(verify_by_definition(SG.build_segments(Pb), Pb))
SG._feature_std = _good
count("特征序列开头丢弃未被发现", 0 if caught else 1, "　（抓到 %d 处）" % caught)
count("BNB 正常版本线段定义复核违规", len(verify_by_definition(SG.build_segments(Pb), Pb)))

# 中枢：v1 只用中心定理一判终结（离开段被算进前中枢），新校验器必须报错
from tools.v1_ref import center_v1, extend_v1
caught = sum(len(check_centers(center_v1.find_centers(R[t]["pens"]), R[t]["pens"])) for t in R)
count("v1 中枢终结方式未被发现", 0 if caught else 1, "　（抓到 %d 处）" % caught)
# 扩展：v1 每合一次就重算区间、区间重叠不合并、级别乱添，新校验器必须报错
caught = sum(len(check_hierarchy(extend_v1.build_hierarchy(R[t]["centers"], R[t]["pens"]), R[t]["centers"], R[t]["pens"]))
             for t in R)
count("v1 扩展合成的毛病未被发现", 0 if caught else 1, "　（抓到 %d 处）" % caught)
# 9 段升级：把一个满 9 段中枢的升级记录抹掉 / 把区间改一点，校验器必须报错
import copy
_stops15 = [s["PI1"] + 1 for s in R["ZEC 15m"]["segs"]]
Zc = copy.deepcopy(R["ZEC 15m"]["centers"])
k9 = next((k for k, z in enumerate(Zc) if z["up"]), None)
if k9 is None:
    # 变异可以把「满 9 段」整个消掉，夹具就造不出来。**这里不编数**：先问检查器对这份
    # 输入有没有话说 —— 有 ⇒ 报它的裁决（那才是真的违规数，别从 StopIteration 后面漏掉）；
    # 它也没话说 ⇒ 报「本格未执行」，绝不写死 1（写死 1 在盲区图上会变成"抓住了"）。
    _n = len(check_centers(Zc, R["ZEC 15m"]["pens"], stops=_stops15))
    for _lab in ("漏掉的 9 段升级未被发现", "算错的升级区间未被发现"):
        if _n:
            count(_lab, _n, "　（没有可动的 up：报检查器对这份输入的裁决）")
        else:
            skip(_lab, "没有任何中枢带 up，夹具造不出，检查器也无话可说")
else:
    Zc[k9]["up"] = []
    count("漏掉的 9 段升级未被发现", 0 if check_centers(Zc, R["ZEC 15m"]["pens"], stops=_stops15) else 1)
    Zc = copy.deepcopy(R["ZEC 15m"]["centers"])
    Zc[k9]["up"][0]["ZG"] += 0.01
    count("算错的升级区间未被发现", 0 if check_centers(Zc, R["ZEC 15m"]["pens"], stops=_stops15) else 1)
# 段内截断的 live 改法：把一个「所在线段结束」的中枢翻回 live=True（复现被审出的那条 bug），校验器必须报错。
# 这一格守的是 check_centers 里「bound < len(units) ⇒ 必须 live=False 且 term='所在线段结束'」那条 ——
# 没有它，段内算又把中间段的中枢标成「仍在延续」，selfcheck 会静默放过（Nova 审 8f61ece 抓的就是这个）。
_cut = next((k for k, z in enumerate(R["ZEC 15m"]["centers"]) if z["term"] == "所在线段结束"), None)
if _cut is None:
    skip("段内截断标成 live 未被发现", "没有任何『所在线段结束』的中枢，夹具造不出")
else:
    Zm = copy.deepcopy(R["ZEC 15m"]["centers"])
    Zm[_cut]["live"] = True
    Zm[_cut]["term"] = "仍在延续"
    Zm[_cut]["status"] = "暂定"
    Zm[_cut]["status_note"] = "仍在延续"
    count("段内截断标成 live 未被发现", 0 if check_centers(Zm, R["ZEC 15m"]["pens"], stops=_stops15) else 1)
# 类中枢首笔方向：把一个中枢的 PI0 往前挪一格（笔严格交替 ⇒ PI0-1 必是同向笔），复核必须报错。
# 这一格守的是 same_dir_starts —— 没有它，把首笔改回与段同向 selfcheck 会静默放过（Nova 审 44d61a8 抓的就是这个）。
_ds = next((k for k, z in enumerate(R["ZEC 15m"]["centers"]) if z["PI0"] > 0), None)
if _ds is None:
    skip("起笔与段同向未被发现", "没有任何 PI0 > 0 的类中枢，夹具造不出")
else:
    Zd = copy.deepcopy(R["ZEC 15m"]["centers"])
    Zd[_ds]["PI0"] -= 1
    count("起笔与段同向未被发现",
          0 if same_dir_starts(Zd, R["ZEC 15m"]["pens"], R["ZEC 15m"]["segs"]) else 1)
# 类中枢跨段：两条变异各一格 —— ① 把 rel 改回全局重算（复现 6eea8c4 的现状）；② 把相邻两段的
# 首尾两个类中枢硬并成一个合成体。cross_seg_links 必须各自报错（它不读 `seg`，所以抹掉 seg 也骗不过它）。
from core.center import classify_pair                          # noqa: E402
Zx = copy.deepcopy(R["ZEC 15m"]["centers"])
_xk = [k for k in range(1, len(Zx)) if Zx[k - 1].get("seg") != Zx[k].get("seg")]
if not _xk:
    skip("跨段 rel 未被发现", "ZEC 15m 没有相邻两段都有类中枢的段界，夹具造不出")
    skip("跨段合成未被发现", "同上")
else:
    for k in range(1, len(Zx)):
        Zx[k]["rel"], Zx[k]["kind"] = classify_pair(Zx[k - 1], Zx[k])
    for z in Zx:
        z.pop("seg", None)
    count("跨段 rel 未被发现", 0 if cross_seg_links(Zx, [], R["ZEC 15m"]["segs"])[0] else 1)
    _a, _b = R["ZEC 15m"]["centers"][_xk[0] - 1], R["ZEC 15m"]["centers"][_xk[0]]
    _bx = [dict(_a, nmerge=2, members=[_a, _b])]
    count("跨段合成未被发现", 0 if cross_seg_links(R["ZEC 15m"]["centers"], _bx, R["ZEC 15m"]["segs"])[1] else 1)
# 买卖点：把一个三买挪到离开段的终点、把一个一买挪到没创新低的位置，复核必须报错
Rz = R["ZEC 15m"]
S = signals(Rz, "pen")
s3 = copy.deepcopy(S)
t = next((x for x in s3 if x["kind"] == "三买"), None)
if t is None:
    # 实测：三买被消光时 check_signals(s3, …) = **0** —— 复核器一个字都没有。
    # 所以这一格报 0 就是假绿，只能报「未执行」（见卡 card-75fbc68f-0c8 的逐站点测量）。
    # 这格**确实有变异踩得到**，不是死代码：`core/pen.py` 的 maxmin（8 处）会把信号总数打成 0。
    # 且这个数在补丁前后一样（main 上 0、合了 signals-blind-spot 之后还是 0）—— 不是"没量过"。
    skip("挪错位置的三买未被发现", "引擎一个三买都没吐，夹具造不出；复核器对此也无话可说")
else:
    t["unit"] -= 1; t["bar"], t["price"] = Rz["pens"][t["unit"]]["i1"], Rz["pens"][t["unit"]]["p1"]
    count("挪错位置的三买未被发现", 0 if check_signals(s3, Rz, "pen") else 1)
s1 = copy.deepcopy(S)
t = next((x for x in s1 if x["kind"] == "一买"), None)
_alt = next((k + 1 for k, z in enumerate(Rz["centers"]) if z["rel"] != "下跌延续"), None)
if t is None or _alt is None:
    # 复核器有没有话说，**取决于是哪种"消光"，所以这里只能按返回值分支，不能写死一个数**：
    #   只把 一买 挑掉、其余点还在（91 个）⇒ check_signals = **3**（三条"二买前面没有一买"）
    #   整个信号列表空掉（`core/pen.py` 的 maxmin 真跑出来的那一态）⇒ **0**，一个字都没有
    # 两个数都在 main 和"合了 signals-blind-spot 之后"各量过一次，**一样** —— 所以这段的顺序
    # 依赖不存在，先合哪支都不影响这两格（我先前在群里担心过它会变，实测没变）。
    # 写死 1 会把上面 3 这个真裁决漏掉；写死 0 会把"工具没在岗"说成"没事"。所以按返回值走。
    _n = len(check_signals(s1, Rz, "pen"))
    if _n:
        count("不在下跌趋势里的一买未被发现", _n, "　（夹具造不出：报复核器对这份输入的裁决）")
    else:
        skip("不在下跌趋势里的一买未被发现", "一买或非下跌中枢不存在，夹具造不出，复核器也无话可说")
else:
    t["center"] = _alt
    count("不在下跌趋势里的一买未被发现", 0 if check_signals(s1, Rz, "pen") else 1)

# 0 轴回抽那个开关：**默认关 ⇒ 复核违规一个数都不许变**；**开了必须真能说话**。
# 两格都要：只测"关着是 0"就是装饰（一个永远绿的开关证明不了自己接上了），
# 只测"开着会红"又证明不了默认没改判。这一对才是那条开关的验收。
_n_off = sum(len(check_signals(signals(Rz, lv, "macd"), Rz, lv, "macd")) for lv in ("seg", "pen"))
_n_on = sum(len(check_signals(signals(Rz, lv, "macd"), Rz, lv, "macd", check_zero_axis=True))
            for lv in ("seg", "pen"))
count("0 轴开关默认关：复核违规", _n_off, "　（关着变过数就是改了判定）")
count("0 轴开关开了却没话说", 0 if _n_on > _n_off else 1,
      "　｜ 开了 = %d 条，关着 = %d 条" % (_n_on, _n_off))

# 断点层（不变量 A）：断点两侧永不合并。校验器必须抓得住「断点被吃掉」；
# 同时切分不得扰动断点之前的结构 —— 各段独立跑，前缀必须逐字段不变。
from core.kline import quantize, standardize, check_no_cross_break_merge
from core.preprocess import preprocess
from config import tick_of

zbars = quantize(json.load(open(data("zec15.json"), encoding="utf-8")), tick_of("zec15.json"))
m0 = standardize(zbars)
merged = [k for k in range(1, len(m0)) if m0[k]["i"] > m0[k - 1]["i"] + 1]   # 所有真合并过原始K线的位置
if not merged:
    # standardize 一次都没吃进多根 K 线（变异能把它弄成这样）⇒ 断点摆不下去，整段夹具没了。
    # 这 5 格**都**依赖那个断点，一起报「未执行」，别让一格把整段拖崩。
    for _lab in ("被吃掉的断点未被发现", "按断点切完仍有跨断点合并",
                 "断点切分没起作用（切完与整段相同）", "断点输出的下标越界",
                 "断点输出的下标未递增"):
        skip(_lab, "standardize 没产生任何「吃进多根」的位置，断点摆不下去")
else:
    k = merged[len(merged) // 2]                                            # 取中段一根，别用序列开头那几根
    b = m0[k]["i"]                                                          # 把断点摆在它吃进去的那根上
    brk = [dict(i=b, reason="mutation")]
    count("被吃掉的断点未被发现", 0 if check_no_cross_break_merge(m0, brk) else 1,
          "　（断点 %d，跨它合并的是第 %d 根）" % (b, k))
    m1 = standardize(zbars, breaks=brk)
    count("按断点切完仍有跨断点合并", len(check_no_cross_break_merge(m1, brk)))
    count("断点切分没起作用（切完与整段相同）", 0 if m1 != m0 else 1)
    count("断点输出的下标越界", sum(1 for x in m1 if not (0 <= x["ih"] <= x["i"] < len(zbars) and 0 <= x["il"] <= x["i"])))
    count("断点输出的下标未递增", sum(1 for a, c in zip(m1, m1[1:]) if c["i"] <= a["i"]))
count("breaks=[] 与整段口径不一致", 0 if standardize(zbars, breaks=[]) == R["ZEC 15m"]["std"] else 1)
_adj, _brk = preprocess(zbars, adjust="none", session=None)
count("preprocess 非恒等（不变量 C1）", 0 if (_adj == zbars and _brk == []) else 1)

# ---- 中枢切分：框不跨走势分界点 ----
# 原来这里跑 tools/cut_check.py 的 span_violations（量的是笔层出刀 cut=turn 的切点）；turn 退役后（card-3edd7fb3-412）
# 这条改由下面 trend_check 的不变量 ②「框不跨分界」（D4-1）守，反向验证在 trend_check --self-test 的 P1。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

# ---- 线段层图头：第一段终点要越过起点（L78:9-10，card-24dd71cb-003）----
# 线上 AAPL 1h 冻成夹具（tools/fixtures/，不放 data/ 免得动到别的基线）：图头第一笔是窗口外上一段的尾巴，
# 按它定方向会划出「向下但终点比起点高」的第一段。修法：图头那一段终点没越过起点就往后挪一笔重划。
print("=" * 72)
import json as _json                                         # noqa: E402
_fx = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"])
       for b in _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "aaplusdt_1h_headdir.json")))]
from config import tick_of as _tick_of                       # noqa: E402
# ★ C3（10-08）默认 6 根以后，这份夹具（当时是 7 根下冻的）在 6 根下不再出这个毛病，data/ 10 份、线上 15 张在 6 根下也**无样本**
#   ⇒ 这一格钉在 7 根档（min_gap=4）上跑：7 根是还在的开关档，修法两档都管。6 根档出了样本再补一份。
_rh = analyze(_fx, tick=_tick_of("aaplusdt_1h.json"), min_gap=4)
count("AAPL 1h 夹具线段不变量违规（图头段方向）", len(check_segments(_rh["segs"], _rh["pens"])))
SG.HEAD_DIR_FIX = False                                       # 反向验证：拿掉这条修法，同一份夹具必须报出来
_rh0 = analyze(_fx, tick=_tick_of("aaplusdt_1h.json"), min_gap=4)
SG.HEAD_DIR_FIX = True
count("拿掉图头段方向修法后 AAPL 1h 夹具没报出来", 0 if check_segments(_rh0["segs"], _rh0["pens"]) else 1)

# ---- 同一家第二种：图头段起点非段内极值、且不是 L78 ① 型（card-2783fa1f-da8，线上 ZEC 4h 10-07）----
# 窄版：判定跟检查器共用 SG._start_check —— 宽版（凡非极值就挪）会把 zec_2h 夹具 191.35 那个合法 ① 型图头挪丢。
_fx4 = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"])
        for b in _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "zecusdt_4h_headext.json")))]
_r4 = analyze(_fx4, tick=_tick_of("zecusdt_4h_headext.json"))
count("ZEC 4h 夹具线段不变量违规（图头段起点非极值）", len(check_segments(_r4["segs"], _r4["pens"])))
SG.HEAD_EXT_FIX = False                                       # 反向验证：拿掉这条修法，同一份夹具必须报出来
_r40 = analyze(_fx4, tick=_tick_of("zecusdt_4h_headext.json"))
SG.HEAD_EXT_FIX = True
count("拿掉图头段起点修法后 ZEC 4h 夹具没报出来", 0 if check_segments(_r40["segs"], _r40["pens"]) else 1)

# ---- 走势分界 v3（docs/spec/走势分段.md v3 §三，card-51571a5f-dc2）----
# 基线（zec15／zec30 五个分界＋一次撤回）、不变量（交替、刀在同向线段终点、两刀间有中枢、框不跨分界、首尾相接）、
# D4-4 见证（笔层一买 1900 不切框）、不看未来。反向验证在 tools/trend_check.py --self-test（spec §四 的 P1／P2／P5 各自必须变）。
import io as _io, contextlib as _ctx                       # noqa: E402
from trend_check import main as _trend_main               # noqa: E402
with _ctx.redirect_stdout(_io.StringIO()) as _tbuf:
    _trc = _trend_main()
count("走势分界 v3 不合 spec", 0 if _trc == 0 else sum(1 for l in _tbuf.getvalue().splitlines() if l.startswith("✗")),
      "　← tools/trend_check.py%s" % ("" if _trc == 0 else "：" + " ｜ ".join(l for l in _tbuf.getvalue().splitlines() if l.startswith("✗"))[:200]))

# ---- J12：走势分段的起点、终点不自动是本级别买卖点（买卖点.md 八.5″，Nova 10-08）----
# 买卖点只由 core/signals.py 出，它不读 core/trend.py 的分界。这里反着守：把分界那一整套换成「一调就炸」，
# 再把 R6 读法来回切，signals 都必须逐条相等 —— 以后谁把分界接进买卖点，这一格先红。
import core.trend as _T                                    # noqa: E402
from core.signals import signals as _sigf                 # noqa: E402
from trend_check import run as _trun                      # noqa: E402
_rj, _ = _trun("zec15.json")
_j12_base = [(s["kind"], s["bar"], s["confirmed"]) for s in _sigf(_rj)]
def _boom(*a, **k):
    raise RuntimeError("signals 读了走势分界")
_j12_bad = 0
_saved = (_T.find_bounds, _T.trend_v3, _T._R6_B)
try:
    _T.find_bounds = _T.trend_v3 = _boom
    for _flag in (True, False):
        _T._R6_B = _flag
        try:
            _j12_bad += [(s["kind"], s["bar"], s["confirmed"]) for s in _sigf(_rj)] != _j12_base
        except RuntimeError:
            _j12_bad += 1
finally:
    _T.find_bounds, _T.trend_v3, _T._R6_B = _saved
count("J12：买卖点随走势分界变了（signals 不许读分界）", _j12_bad, "　（zec15，%d 个点）" % len(_j12_base))

# ---- J18：高级别的改变必须先从低级别开始（级别联动.md 七，Nova 10-08）—— **只报警，不进违规数** ----
# 判法和为什么这么判见 tools/j18_check.py 文件头；反向臂（小周期上下翻转 ⇒ 每刀都报）在它的 --self-test。
from j18_check import main as _j18_main                  # noqa: E402
with _ctx.redirect_stdout(_io.StringIO()) as _jbuf:
    _j18_v = _j18_main()
print("  J18 级别先后（只报警）           : %d 处违反%s" % (_j18_v, "" if not _j18_v else "　← tools/j18_check.py：" +
      " ｜ ".join(l.strip() for l in _jbuf.getvalue().splitlines() if l.strip().startswith("违反"))[:200]))

# ---- J19：相邻周期的笔状态联动（级别联动.md 七 J19，Nova 10-08）—— **只报警，不进违规数** ----
# 只跑 1h 对 4h 那一对（几秒）；15m 那两对 --full 才跑。判法和翻转臂见 tools/j19_check.py 文件头。
from j19_check import main as _j19_main                  # noqa: E402
with _ctx.redirect_stdout(_io.StringIO()) as _j19buf:
    _j19_v = _j19_main()
print("  J19 笔状态联动（只报警）         : %d 处违反%s" % (_j19_v, "" if not _j19_v else "　← tools/j19_check.py：" +
      " ｜ ".join(l.strip() for l in _j19buf.getvalue().splitlines() if l.strip().startswith("违反"))[:200]))

# ---- 判据前提：下面那扇「字体覆盖」门自己的基准对不对 ----
# 那扇门判「缺不缺字」靠 `config._notdef_mask` 投出的 .notdef 基准。基准错了它就是**假绿**：
# 拿一个没有墨的空白遮罩当 .notdef，所有真字形都"不等于它" ⇒ 报「一个都不缺」。
# 所以这一格既不是引擎不变量（不记进 FAIL）、也不是字体环境（不记进 FONT_GAPS）——
# 它是**判据自己的前提**，给它自己的数：混进任何一个都说不清是谁的问题。
# 位置也必须是这里 —— 跑在那扇门**前面**：先说清基准可不可信，那扇门的数才有得读。
print("=" * 72)
# ★ 这一格**不止一个前提**（config 的 .notdef 基准 ／ undef 那把尺自己的判据），而它们的
#   **处置不一样**：一个叫你去修 config 的基准，一个叫你去修扫描器。所以这里收的是
#   **一张表**（谁坏了 + 坏了该怎么办），不是一个 0/1 —— @atlas-791f 908 量到的正是这个：
#   原来 `PREMISE` 是**一个数背两个前提**，而汇总那句的字面串只认识 config ⇒ undef 坏了的时候
#   它印「config._notdef_mask 自测不过」，**指错文件、指错动作**。同一个形状（并两个不同东西、
#   却只留一个名字）就是今晚 `FONT_GAPS`/`FONT_FILES` 那次 —— 那次并的是量纲，这次并的是前提。
#   `PREMISE` 那个汇总数**留着**（退出那格需要一个值），但**话由这张表说**。
PREMISES = []          # [(名字, 状态, 处置句)] —— 状态 0=过 ／ 1=不过 ／ -1=跑不了
# ★ 处置句**不许指方向**（「上面那扇门」「下面那把尺」这种）—— 它印在哪儿由**印的地方**决定
#   （现在只印在文末汇总那段，但那是印的地方的事，不是这张表的事）。
#   实测（card-6adfd2c9-dca，@atlas-791f ① 那处）：句子从「就地印」搬进这张表时，
#   位置词没跟着搬 —— 编出来的时候下面还有一排 `[尺]` 行，可汇总段**在那一排下面**
#   ⇒ `[判据前提] … 下面那把 `undef` 尺 …` 这句话在默认报告里**指反了**（[尺] 行在它上方）。
#   ⇒ 处置句一律**点名**（`[字体覆盖]` / `[尺] undef`），不点位置。加一句新处置 = 照这个写。
try:
    from tools.verify_notdef import run as _notdef_selftest
    _n_bad = _notdef_selftest(verbose=False)        # 通过的格不逐条打（一屏已经很长），不过的永远打
    if _n_bad:
        PREMISES.append(("config._notdef_mask 自测", 1,
                         "`[字体覆盖]` 那扇门的基准本身是错的，那扇门的数不可读（先修基准）"))
        print("[判据前提] config._notdef_mask 自测：%d 格不过 ← 下面那扇字体覆盖门的基准本身是错的" % _n_bad)
        print("           那扇门会把真缺的字报成「一个都不缺」（静默假绿）。**先修基准，再读那扇门。**")
    else:
        PREMISES.append(("config._notdef_mask 自测", 0, ""))
        print("[判据前提] config._notdef_mask 自测通过 ⇒ 下面那扇门拿的 .notdef 基准可信")
except Exception as e:
    PREMISES.append(("config._notdef_mask 自测", -1,
                     "`[字体覆盖]` 那扇门的基准没人验过（先修基准）"))
    # ★ 这两行原来不点主语（`[判据前提]` 是**格子名**，不是那扇门的名字），而第二行又用「那扇门」
    #   回指 —— 那行里没有先行词 ⇒ 单看这两行读不出"哪扇门的哪件事没跑成"。
    #   同一格另外两行（`自测：%d 格不过` / `自测通过`）与下面那条兄弟前提（`undef_scan 自测跑不了`）
    #   **都点了主语** ⇒ 照它们补（`card-0142dfdd-bdd`）。
    # ★ 并且**不许用位置词**：处置句一律**点名**（`[字体覆盖]` / `[尺] undef`）、**不点位置**。
    print("[判据前提] config._notdef_mask 自测跑不了：%s" % e)
    print("           自测没跑成 = `[字体覆盖]` 那扇门拿的 .notdef 基准没人验过 ⇒ 按「查不出来不算通过」计。")

# 第二条前提（card-6adfd2c9-dca）：下面那把 `undef` 尺**自己**有没有判据。
# 它唯一的死法是**假报**（假红一次之后没人信它），另一个方向的死法是**真有 bug 看不见**
# （那这格子只是个安慰奖）。两个方向都得有实测 ⇒ 八个探针 + 一对同树成对读数。
# ★ 必须**自动**跑：@atlas-791f 那条 T7 量的正是"不自己带 rc 的判据会变成又一个只在某分支才炸的洞"
#   —— 手跑一次的读数会过期，接线才会跟着每一次 selfcheck 跑。
try:
    from tools.undef_scan import run as _undef_selftest, selftest_paired as _undef_paired
    _u_bad = _undef_selftest(verbose=False)      # 八个探针：假报形状不许报、真形状必须报
    _u_bad += _undef_paired(verbose=False)       # 成对读数：同一棵树上 +1 个探针 ⇒ 正好多 1 处并点名
    if _u_bad:
        PREMISES.append(("undef_scan 自测", 1,
                         "`[尺] undef` 那条**自己的判据坏了**，它那份「0 处」不可读"
                         "（先修扫描器，不是去修它扫出来的东西）"))
        print("[判据前提] undef_scan 自测：**%d 格不过** ← 下面那把尺那份「0 处」不可读" % _u_bad)
    else:
        PREMISES.append(("undef_scan 自测", 0, ""))
        print("[判据前提] undef_scan 自测通过（探针全对 + 同树成对读数成立）⇒ 下面那把尺报的数可信")
except Exception as e:
    PREMISES.append(("undef_scan 自测", -1, "`[尺] undef` 那条自己没验过 ⇒ 它那份「0 处」不可读"))
    print("[判据前提] undef_scan 自测跑不了：%s" % e)
    print("           尺自己没验过 ⇒ 它那份「0 处」按「查不出来不算通过」计。")

# 汇总数（退出那格要一个值）：-1 优先于 1 ——「跑不了」比「不过」更不可读。
PREMISE = (-1 if any(_s < 0 for _, _s, _ in PREMISES)
           else (1 if any(_s > 0 for _, _s, _ in PREMISES) else 0))

# ---- 字体覆盖：上面每一条都默认「字画得出来」，这一步才验那个默认 ----
# 缺字是**静默**失败：PIL 画成方框、不报错，然后上面照样报「全部通过」。所以它不计进
# FAIL（FAIL 是引擎不变量的数目，两者含义不同，混成一个数就说不清是谁的问题），
# 但它一样让退出码非 0：查不出来，就不算通过。
print("=" * 72)
FONT_GAPS = 0
FONT_FILES = 0
try:
    # ★ `ROOT` 必须**跟着进来**：`scan()` 返回的 `_p` 是 fontcheck 的绝对路径，
    #   而这行拿 `os.path.relpath(_p, ROOT)` 印它 —— 下面 `if _skipped:` 那段一跑就 NameError。
    #   而「有文件没扫成」**恰好就是那段存在的理由** ⇒ 干净树上这行永远不跑 ⇒ 隐性（不是已修）。
    #   不自己再算一份 `ROOT`：同一个量两个定义，本仓反复栽的那个形状（@iris-64a1 的甲案）。
    from tools.fontcheck import scan, ROOT
    _font, _missing, _conflict, _n, _files, _skipped = scan()
    # ★ 这里原来是**一个数**：`len(_missing) + len(_conflict) + len(_skipped)` —— 前两项的单位是
    #   **字符**、第三项是**文件**。加成一个数之后它**没有量纲**，而下游三处（✗ 那行／总账行／
    #   退出那格）**一律按"字符"说话** ⇒ 那份报告在说一件它没量过的事。
    #   实测（@nova-8980 造的变异：一行语法坏的文件）：1 个**文件**没扫成、0 个**字符**缺
    #   ⇒ 报告印「1 个字符画不出来」+「先去换 ttf」，而真事是那张卡**根本没进分母**，换字体治不了。
    #   ⇒ 数字是 1、处置是错的，比数错了更难发现（数错了有人会去核，处置错了不会）。
    # ⇒ 拆成两格、各自带量纲。`_missing` 与 `_conflict` 相加**不重数**：render/style.py:154 是
    #   if/elif 二选一，且 glyph_gaps 的 docstring 写明 conflict「不并进 missing」。
    FONT_GAPS = len(_missing) + len(_conflict)      # 单位：个**字符**
    FONT_FILES = len(_skipped)                      # 单位：个**文件**（和上面不是一回事，别加）
    print("[字体覆盖] %s  （扫了 %d 个脚本%s）"
          % (getattr(_font, "path", "?"), _files,
             "，**跳过 %d 个**" % len(_skipped) if _skipped else ""))
    if _skipped:
        for _p, _e in _skipped:
            print("  ! 没扫成 %s —— %s" % (os.path.relpath(_p, ROOT), _e))
        print("    这几个文件的字一个都没进来，缺字结论不完整 —— 按「查不出来不算通过」计进违规。")
    if _missing:
        print("  ✗ 会画上去的字符串里 %d 个不同字符，有 %d 个画不出来：%s"
              % (_n, len(_missing), "".join(_missing[:40]) + ("…" if len(_missing) > 40 else "")))
    if _conflict:
        print("  ⚠ cmap 与渲染分歧 %d 个：%s" % (len(_conflict), "".join(_conflict[:20])))
    if _missing or _conflict:
        # ★ 这段的触发条件原来是 `if FONT_GAPS:` —— 含"只有文件没扫成"那一档，于是 ✗ 后面的数会是
        #   **0**（真的缺 0 个字），而它底下让人去换 ttf。修的是"报告消失"，这条修的是"报告说谎"：
        #   ✗ 和它下面那句只许在**真有缺字**时出现。
        print("    这些字会变成方框且不报错。**这是字体/环境问题，不是引擎问题** ——")
        print("    先用 CHANLUN_FONT 指一份含中日韩字形的 ttf 再跑。")
        print("    若换了好字体**还剩几个**，那就不是环境问题，是**卡片用了这份字体没有的符号**")
        print("    （实测：Noto Sans CJK 有 ✓ U+2713，但没有 ✔ U+2714 / ✗ U+2717 / ✘ U+2718）。")
    elif _skipped:
        # 只走了这一支 ⇒ 一个字符都没缺。单独一句、**不给换字体的建议**（换字体治不了没解析成的文件）。
        # 上面 `if _skipped:` 那段已经逐条点了文件名和理由，这里只把它计进违规这一层说清。
        print("  ✗ 有 %d 个文件没扫成 ⇒ 缺字结论不完整（按「查不出来不算通过」计）" % len(_skipped))
    else:
        print("  ✓ 这份字体画得出字面量里的全部字符")
except Exception as e:
    FONT_GAPS = -1
    FONT_FILES = -1
    print("[字体覆盖] 查不了：%s" % e)

# ---- 警告措辞：上面那扇门报出来的缺字，措辞有没有把「探针类」说成「本轮的图」----
# 它既不是引擎不变量（不记进 FAIL）、也不是字体环境（不记进 FONT_GAPS）——
# 它是**那句话本身的分寸**，给它自己的数：混进任何一个都说不清是谁的问题。
# 为什么要挂它（2026-09-30 实测）：`tools/verify_warn.py` 跟着
# `agent/atlas/warn-incomplete-wording` 进了 main，但**没有任何门调用它** ——
# selfcheck 里 `verify_warn` 出现 0 次，全仓只有 config.py 的一条注释提到它。
# ⇒ 有人把措辞改回陈述句，不会有任何东西红。**文件在仓里 ≠ 它在跑。**
# 位置在这一格：它验的是上面那扇门打出来的那句话，那扇门先说完，措辞才有得读。
print("=" * 72)
WARN_WORDING = 0
try:
    from tools.verify_warn import run as _warn_selftest
    _w_bad = _warn_selftest(verbose=False)
    if _w_bad:
        WARN_WORDING = 1
        print("[警告措辞] 自测 %d 格不过 ← 缺字警告把「探针类代表字」说成了「本轮的图会出方框」" % _w_bad)
        print("           那是**对正确的活报错**：本轮压根没画到那些字（上面那扇门 rc=0 就是证据）。")
    else:
        print("[警告措辞] 探针类缺字只作条件陈述，且点明了是哪一份名单")
except Exception as e:
    WARN_WORDING = -1
    print("[警告措辞] 跑不了：%s" % e)
    print("           自测没跑成 = 那句话的分寸没人验过 ⇒ 按「查不出来不算通过」计。")
# ---- 版式体检：上面每一条判「数对不对」，这一条判「画出来的字有没有出框」 ----
# 为什么要有这一条：`tools/cardfit.py` 是今晚全队所有版式结论的那把尺，而 selfcheck 里
# **0 次**引用它 ⇒ **尺退化没有任何自动发现机制**（@atlas-791f 那条 verify_warn 是同一形状，
# 区别只是那把尺至少会自己印一句「注入 0 支」）。手跑的数是真的，但手跑不能发现"尺坏了"。
# 它不并进 FAIL（FAIL 是引擎不变量的数目），也不并进 FONT_GAPS（那是字体环境）——
# 各给各的数，混成一个就说不清是谁的问题。
print("=" * 72)
# ---- 尺子：**每把起一个子进程，各读各的桶** ------------------------------------
# 上一版把几把尺的输出**拼成一个大 list**，再用 `startswith("[版式体检]")` 这类**前缀**去里面捞。
# ⇒ 那是拿"行文本的形状"当接口：两把尺一旦有同前缀的行就**串台**。实测（`05f3e24` 上，
#   把两把尺的输出按两种顺序拼起来，收集逻辑逐字照抄本文件）：
#     `合计` 撞桶   卡片尺先跑 ⇒ `int(_tot[-1].split()[1])` 抛 **ValueError: …'条'**；
#                   undrawn 先跑 ⇒ `_tot[-1]` 是卡片尺那行 ⇒ **静默读到它的 0**，看起来一切正常。
#     `[分支覆盖]`  撞桶 ⇒ `_cov[0]` **只取第一条** ⇒ 换个顺序，**另一把尺那行消失**。
#                   ⇒ 两种顺序下"消失"**必发生一次**：同一个 bug 的两副面孔。
# ⇒ 改成**按子进程分桶**：每把尺只在自己的输出里找自己的行。
# ⇒ 加第 N 把尺 = `SCALES`/`GATES` 表里加一行（不再伸手去改前缀白名单 —— 那正是本卡要拆的硬编码面）。
GATES = [
    # (短名, 脚本, 它报的那个数是什么, 单位, "这个数读得懂"的证据行前缀, 取数的正则, 旧格式?)
    # `旧格式` 那一格是**过渡用的**：cardfit 那三行的格式和语义一个字不改（别人卡面上的接受判据
    # 读的就是它们），等它的接受判据也改过来，这一格连着那三行一起删。
    ("cardfit", "cardfit.py", "卡片文字越界/出框", "处", "[版式体检]",
     r"^合计\s+(-?\d+)", True),
    ("undrawn", "cardfit_undrawn.py", "所有跑法都没画到的字面量", "条", "[量法/对象]",
     r"^合计.*：\s*(-?\d+)\s*条\s*$", False),
    # 第三条尺（card-6adfd2c9-dca）：不跑代码、只读 AST，扫「用了但没定义的名字」。
    # 为什么要它：`tools/selfcheck.py:250` 的 `ROOT` 那种 NameError 干净树上**永远不跑**
    # （触发条件在 `if _skipped:` 里）⇒ 靠跑跑不出来，靠人翻才翻得到。本仓没 CI、pyflakes 也装不上。
    ("undef", "undef_scan.py", "用了但没定义的名字", "处", "[量法/对象]",
     r"^未定义名：(-?\d+) 处$", False),
]
LAYOUT = 0     # ← 语义**不变**：cardfit 的越界处数（接受判据里 `版式=N` 读的就是它）
SCALES = 0     # 新列：**有几把尺报红或查不了**（0 = 表里每一把都 rc=0 且报出了证据行+数）
ROWS = []      # 每把尺一行，逐把印出来（谁红谁绿，不再靠猜）
try:
    import subprocess
    import re as _re
    _here = os.path.dirname(os.path.abspath(__file__))
    for _name, _fn, _what, _unit, _ev, _rx, _legacy in GATES:
        # 跑的就是人平时跑的那条命令（子进程），不另抄一份调用序 —— 否则门和人玩的不是同一把尺。
        _p = subprocess.run([sys.executable, os.path.join(_here, _fn)],
                            capture_output=True, text=True)
        _lines = ((_p.stdout or "") + (_p.stderr or "")).splitlines()
        _vid = [l for l in _lines if l.startswith(_ev)]
        _nums = [m.group(1) for l in _lines for m in [_re.match(_rx, l)] if m]
        # 三样都齐（rc / 证据行 / 自己的数）才叫"这把尺报了数"：
        #   缺一样就是"查不出来不算通过"，**不能拿 0 顶上**（那正是本仓反复栽的那个形状）。
        _why = None
        if not _vid:
            _why = "没打出证据行（%s）：这个数读不读得懂没人验" % _ev
        elif not _nums:
            _why = "没报出「合计」，或那行读不出数"
        _val = int(_nums[-1]) if _nums else None
        # ★ 尺**自己的理由行**。原来红的时候只印「<我写死的标签> <合计那个数>」，于是：
        #   两把尺这次 rc=1 都出自「没声明 1 张」，可合计那行是 0（实测 2026-09-30），
        #   印出来就成了「它自己说有问题：卡片文字越界/出框 0 处」——**有名字可点，没点**。
        #   而理由行它自己早印了（cardfit `退出原因: …` ／ undrawn `[rc=1] …：1 张`）。
        # ⇒ 按**行首约定**找它，找不到才退回原来那个数。**不给每把尺配一条正则** ——
        #   配正则就是"加一把尺要人去别处登记"，② 拆掉的前缀白名单正是这个形状。
        _rsn = None
        # ★ 尺自己**点了名**的行，逐条收：`✗ <卡名>（<原因>）` 和 `[rc=<n>] <类名>：<数><单位>`。
        #   判据要的是**两条通道**：rc 说"有事" ＋ 点名说"是什么"。只把 rc 带进聚合器、名字留在
        #   子进程的 stdout 里，等于把定位成本推回给读报告的人（@atlas-791f 876 在 c923c9f 上量的：
        #   透过来 **0 行** —— 报告里那句"（上面是它的原文）"指向了不存在的"上面"）。
        #   按**行首约定**认这两类，不给每把尺配正则 —— 配正则就是"加一把尺要人去别处登记"，
        #   ② 拆掉的前缀白名单正是这个形状。认不出的行不猜、也不补。
        _named = []
        for _l in _lines:
            _s = _l.strip()
            if _s.startswith("✗ ") or _s.startswith("[rc="):
                _named.append(_s)
            if _rsn is None and (_s.startswith("[rc=") or _s.startswith("退出原因:")):
                _rsn = _s
        _rc = _p.returncode
        if _rc != 0 or _why is not None:
            SCALES += 1
        ROWS.append((_name, _rc, _val, _why, _what, _unit, _rsn, _named))
        if _legacy:
            # 这三行的**格式和语义一个字不改** —— 别人卡面上的接受判据读的就是它们。
            if _vid:
                print(_vid[0])
            if _why is None:
                LAYOUT = _val
            else:
                # 这一行是**这个数读不读得懂**的前提：同一棵树 Droid 0 处 / Noto 13 处，
                # 不带字体的「0 处」和「13 处」在纸面上分不出来（stock 尺就是这个状态）。
                LAYOUT = -1
                print("[版式] 尺没打字体那行 ⇒ 下面的数不可读，按「查不出来不算通过」计")
            print("[版式] 卡片文字越界/出框：%d 处（应为 0）" % LAYOUT if LAYOUT >= 0
                  else "[版式] 卡片文字越界/出框：查不了")
            _cov = [l for l in _lines if l.startswith("[分支覆盖]")]
            if _cov:
                print("       %s" % _cov[0])
    # 每把尺一行：**名字 / rc / 它自己那个数 / 红没红**。旧版只有 cardfit 一行，
    # 其余几把尺"接上了没有"在报告里看不出来（@atlas-791f 那张表就是这么量出来的）。
    # ★ 这一行也是"加了第 N 把尺"的落点：表里加一行，这里自己多印一行。
    for _name, _rc, _val, _why, _what, _unit, _rsn, _named in ROWS:
        _head = "[尺] %-8s rc=%s" % (_name, _rc)
        if _why is not None:
            print("%s  **查不了**：%s" % (_head, _why))
        elif _rc != 0 and _rsn:
            # 引它自己那行（**逐字**），不再复述成我写的标签 + 合计那个数。
            print("%s  **它自己说有问题**：%s" % (_head, _rsn))
        elif _rc != 0:
            # 它没印理由行 —— 这一档本身要说出来：**红得有理由行可点**才是新口径的卖点。
            print("%s  **它自己说有问题**：%s %d %s（★ 但它**没印理由行**，这句是我按合计那个数复述的）"
                  % (_head, _what, _val, _unit))
        else:
            print("%s  %s：%d %s" % (_head, _what, _val, _unit))
        # ★ 红／查不了时，把它自己点名的行**逐条透出来**（`_rsn` 上面那行已经印过，不印两遍）。
        #   这一跳原来把尺的名字全丢了：rc 到了、`✗ <卡名>（…TypeError…）` 没到 —— 判据写的
        #   "rc 说有事 ＋ 点名说是什么"在最后一跳只剩一半。透传，不加工。
        if _why is not None or _rc != 0:
            for _l in _named:
                if _l != _rsn:
                    print("      │ %s" % _l)
except Exception as e:
    LAYOUT = -1
    SCALES = len(GATES)
    print("[版式] 跑不了：%s" % e)

print("=" * 72)
print("总违规数:", FAIL, "→", "引擎检查全部通过" if FAIL == 0 else "有问题，需排查")
if SKIP:
    print("未执行数:", SKIP, "→ **有格子的判据压根没跑**（夹具/前提没造出来）")
    print("           这一条不是通过：上面每一行「未执行」都要有人去查为什么造不出夹具。")
# ★ 这两格**分开发言**、各带各的量纲，因为它们的**处置不一样**：
#   缺字 → 换字体（或改卡片用了冷僻符号）；文件没扫成 → 先修那份文件，**换字体治不了**。
#   合成一句就必然借其中一个的量纲说话，那正是原来那句「%d 个字符画不出来」的来路。
# ★ `-1` 那格（字体/扫描整个读不出来）**只印一句**、且**不点名任何处置**（`card-d9205416-2b0`；
#   判据 @nova-8980 884、触发法 @iris-64a1 880 ④ ＋ 886）。原因是上面那两句的前提在这格上**都不成立**：
#   这一格**两件事都不知道** —— 不知道缺不缺字、也不知道有没有文件没扫成 ⇒ 借哪一边的处置都是猜的。
#   原来它印**两句同一个标题**：一句叫你去换 ttf、一句叫你先修文件，而第一句还写着"见上面几行"——
#   上面并没有那几行（@iris-64a1 在 tree `41b8939` 上量到的）。
#   ⇒ 这就是同一个病（「**不知道**」借「**知道**」的措辞说话）在这格上的第二副本。
if FONT_GAPS < 0 or FONT_FILES < 0:
    print("字体覆盖:", "查不了（不算通过）",
          "→ 这份字体/扫描本身就没读出来 ⇒ **缺字结论没有**，先修环境再谈（这条不是结论，是缺口）")
else:
    if FONT_GAPS:
        print("字体覆盖:", "%d 个字符画不出来" % FONT_GAPS,
              "→ 出图会静默出方框（处置：换一份含中日韩字形的 ttf，见上面那几行）")
    if FONT_FILES:
        print("字体覆盖:", "%d 个文件没扫成" % FONT_FILES,
              "→ 那几份文件的字**一个都没进分母**，缺字结论不完整（**换字体治不了**：先修那份文件）")
if PREMISE:
    # ★ 名字和处置都从 `PREMISES` 来，**一个字都不写死**：坏的是哪个前提，就说哪个、说那个的处置。
    #   （写死过一个 → @atlas-791f 908 量到它指错文件、指错动作；见上面 `PREMISES` 那段注释。）
    #   名字本身就是"<谁> 自测" ⇒ 这里拼**不过**（不拼"自测不过"，否则读成"…自测：自测不过"）。
    #   ⚠ 这里原来写着「config 那一句拼出来和原来**逐字相同**」—— 那句话**实测不成立**（@atlas-791f ①）：
    #     名字那半确实逐字相同（`config._notdef_mask 自测` + `不过` = 原来那一串），但**整行**还含处置句，
    #     而处置句是**重打**的、掉了「上面」两个字 ⇒ 断言写大了，断的是整行、验的只有半行。
    #     现在处置句**故意**不再逐字相同：改成点名（见上面 `PREMISES` 那段），因为那张表会印在别处。
    for _pn, _ps, _pact in PREMISES:
        if _ps:
            print("判据前提:", "%s%s" % (_pn, "跑不了（不算通过）" if _ps < 0 else "不过"),
                  "→ %s" % _pact)
if WARN_WORDING:
    print("警告措辞:", "跑不了（不算通过）" if WARN_WORDING < 0 else "自测不过",
          "→ 缺字警告会把探针类缺字说成本轮的图（对正确的活报错）")
# 退出码只说"有东西不对"，不说"是谁不对"：三个数混在一个非 0 里，读的人猜不出来。
# 这是 @iris-64a1 指出的洞 —— 在字体门本来就会红的机器上，干净跑和变异跑都是 exit=1，
# 光看退出码**隔离不出** SKIP 有没有生效。打这一行：每个非 0 退出自己说出原因。
if LAYOUT < 0:
    print("版式体检: 查不了（不算通过） → 尺没跑起来，或它没说出自己是哪支字体量的 ⇒ 本格没有可读的数")
elif LAYOUT:
    print("版式体检: %d 处文字越界/出框 → 那几处是卡片版式问题（上面那行写了是哪支字体量出来的）" % LAYOUT)
# ★ 新列：**表里每一把尺**有没有报出数（rc=0 且证据行+数都在）。上面那行只管 cardfit 一把 ——
#   旧版"接上了没有"在报告里**看不出来**：接了一把 rc 恒非 0 的尺，全篇一个字不变、exit 也不变。
if SCALES:
    # ⚠ 措辞：这里是**两件事共用一个数**（`rc≠0` ／ `查不了`）—— 说"没报数"会把"报了数但红了"
    #   那句也盖进去（实测：red 那支印着「：7 条」却也被算进来）。所以只说"不过"，具体哪一种是上面那几行。
    print("尺子: %d 把里 **%d 把不过**（rc≠0 或查不了，两种都在上面 `[尺]` 那几行里点过名）"
          % (len(GATES), SCALES))
# ★ 这一格原来是**手写的**：同一组列名在这两行里各写一遍（`:352` 的格式串 + `:358` 的布尔），
#   实测两行的**集合相同、顺序不同**（前两个对调）、相距 6 行、**0 个测试在守**（@atlas-791f 量的）。
#   它和"前缀白名单"是同一个形状：**加一格要人去两个地方补，漏一处不报错**。
# ⇒ 现在列名只写一遍（下面这张表），格式串和退出码都由它生成。
#   加第 8 列 = 表里加一行 ⇒ **右边自己多一格、布尔自己多一项**（和尺侧 `checks` 同形）。
def _fmt(name, val, neg_word, zero_word):
    """-1 那档的说法不是"0"也不是"不过"：是"**根本没量成**" —— 它必须和"量完是 0"在纸面上分开。"""
    if neg_word and val < 0:
        return "%s=%s" % (name, neg_word)
    if zero_word is not None:
        return "%s=%s" % (name, zero_word if val == 0 else "不过")
    return "%s=%d" % (name, val)

COLS = [
    # (名字, 值, 值<0 时怎么说, "OK/不过" 那档的 OK 怎么说；None = 直接印数)
    ("总违规",   FAIL,         None,     None),
    ("未执行",   SKIP,         None,     None),
    ("判据前提", PREMISE,      "跑不了", "OK"),
    ("警告措辞", WARN_WORDING, "跑不了", "OK"),
    # 下面这两格必须分开：`字体缺字` 的单位是**个字符**、`字体没扫成` 的单位是**个文件**。
    # 原来它们和成 `字体缺字=1` 出去 ⇒ 那句"1 个字符画不出来"是**借来的量纲**，1 其实是文件数。
    # 也不能把 `没扫成` 从退出面上删掉：那样"有文件没扫成"就退回 exit=0 —— 正是本仓那个病。
    ("字体缺字",  FONT_GAPS,  "查不了", None),   # 个字符
    ("字体没扫成", FONT_FILES, "查不了", None),   # 个文件
    ("版式",     LAYOUT,       "查不了", None),
    ("尺子",     SCALES,       None,     None),
]
if len(COLS) != len(set(n for n, _, _, _ in COLS)):
    # 重名 ⇒ 退出那行点不出是哪一个。静态检查，和第 4 格那个单位同理：靠"记得"就会漏。
    raise RuntimeError("COLS 里有重名：%r" % ([n for n, _, _, _ in COLS],))
_bad_cols = [n for n, v, _, _ in COLS if v]
_rc = 1 if _bad_cols else 0
print("退出原因: %s  ⇒ exit=%d" % ("  ".join(_fmt(n, v, nw, zw) for n, v, nw, zw in COLS), _rc))
sys.exit(_rc)
