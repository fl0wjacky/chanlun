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
from core.signals import signals, check_signals

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
    count("线段不变量违规", len(check_segments(S, P)))
    count("线段定义复核违规", len(verify_by_definition(S, P)),
          "　｜ 诊断：终点非段内极值 %d（原文未要求，只报数）" % len(nonextreme_endpoints(S)))
    # 中枢层
    count("类中枢不变量违规", len(check_centers(r["centers"], P)))
    count("类中枢扩展合成违规", len(check_hierarchy(r["big"], r["centers"], P)))
    count("买卖点复核违规", sum(len(check_signals(signals(r, lv, m), r, lv)) for lv in ("seg", "pen") for m in ("macd", "slope")))
    count("线段中枢不变量违规", len(check_centers(r["seg_centers"], [s for s in S if not s.get("live")])))

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
_good, SG._feature_std = SG._feature_std, lambda xs, up: [dict(x, ih=x["i"], il=x["i"]) for x in standardize(xs)]
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
Zc = copy.deepcopy(R["ZEC 15m"]["centers"])
k9 = next((k for k, z in enumerate(Zc) if z["up"]), None)
if k9 is None:
    # 变异可以把「满 9 段」整个消掉，夹具就造不出来。**这里不编数**：先问检查器对这份
    # 输入有没有话说 —— 有 ⇒ 报它的裁决（那才是真的违规数，别从 StopIteration 后面漏掉）；
    # 它也没话说 ⇒ 报「本格未执行」，绝不写死 1（写死 1 在盲区图上会变成"抓住了"）。
    _n = len(check_centers(Zc, R["ZEC 15m"]["pens"]))
    for _lab in ("漏掉的 9 段升级未被发现", "算错的升级区间未被发现"):
        if _n:
            count(_lab, _n, "　（没有可动的 up：报检查器对这份输入的裁决）")
        else:
            skip(_lab, "没有任何中枢带 up，夹具造不出，检查器也无话可说")
else:
    Zc[k9]["up"] = []
    count("漏掉的 9 段升级未被发现", 0 if check_centers(Zc, R["ZEC 15m"]["pens"]) else 1)
    Zc = copy.deepcopy(R["ZEC 15m"]["centers"])
    Zc[k9]["up"][0]["ZG"] += 0.01
    count("算错的升级区间未被发现", 0 if check_centers(Zc, R["ZEC 15m"]["pens"]) else 1)
# 买卖点：把一个三买挪到离开段的终点、把一个一买挪到没创新低的位置，复核必须报错
Rz = R["ZEC 15m"]
S = signals(Rz, "pen")
s3 = copy.deepcopy(S)
t = next((x for x in s3 if x["kind"] == "三买"), None)
if t is None:
    # 实测：三买被消光时 check_signals(s3, …) = **0** —— 复核器一个字都没有。
    # 所以这一格报 0 就是假绿，只能报「未执行」（见卡 card-75fbc68f-0c8 的逐站点测量）。
    skip("挪错位置的三买未被发现", "引擎一个三买都没吐，夹具造不出；复核器对此也无话可说")
else:
    t["unit"] -= 1; t["bar"], t["price"] = Rz["pens"][t["unit"]]["i1"], Rz["pens"][t["unit"]]["p1"]
    count("挪错位置的三买未被发现", 0 if check_signals(s3, Rz, "pen") else 1)
s1 = copy.deepcopy(S)
t = next((x for x in s1 if x["kind"] == "一买"), None)
_alt = next((k + 1 for k, z in enumerate(Rz["centers"]) if z["rel"] != "下跌延续"), None)
if t is None or _alt is None:
    # 实测：一买被消光时 check_signals(s1, …) = **3** —— 复核器自己有话说。
    # 那就报它的裁决，别写死 1（等于把 33 / 3 这两个真裁决从 StopIteration 后面漏掉）。
    _n = len(check_signals(s1, Rz, "pen"))
    if _n:
        count("不在下跌趋势里的一买未被发现", _n, "　（夹具造不出：报复核器对这份输入的裁决）")
    else:
        skip("不在下跌趋势里的一买未被发现", "一买或非下跌中枢不存在，夹具造不出，复核器也无话可说")
else:
    t["center"] = _alt
    count("不在下跌趋势里的一买未被发现", 0 if check_signals(s1, Rz, "pen") else 1)

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

# ---- 字体覆盖：上面每一条都默认「字画得出来」，这一步才验那个默认 ----
# 缺字是**静默**失败：PIL 画成方框、不报错，然后上面照样报「全部通过」。所以它不计进
# FAIL（FAIL 是引擎不变量的数目，两者含义不同，混成一个数就说不清是谁的问题），
# 但它一样让退出码非 0：查不出来，就不算通过。
print("=" * 72)
FONT_GAPS = 0
try:
    from tools.fontcheck import scan
    _font, _missing, _conflict, _n, _files = scan()
    FONT_GAPS = len(_missing) + len(_conflict)
    print("[字体覆盖] %s  （扫了 %d 个脚本）" % (getattr(_font, "path", "?"), _files))
    if FONT_GAPS:
        print("  ✗ 字面量里 %d 个不同字符，有 %d 个画不出来：%s"
              % (_n, len(_missing), "".join(_missing[:40]) + ("…" if len(_missing) > 40 else "")))
        if _conflict:
            print("  ⚠ cmap 与渲染分歧 %d 个：%s" % (len(_conflict), "".join(_conflict[:20])))
        print("    这些字会变成方框且不报错。**这是字体/环境问题，不是引擎问题** ——")
        print("    把 CHANLUN_FONT 指到含中日韩字形的 ttf 再跑，这一步应回 0。")
    else:
        print("  ✓ 这份字体画得出字面量里的全部字符")
except Exception as e:
    FONT_GAPS = -1
    print("[字体覆盖] 查不了：%s" % e)

print("=" * 72)
print("总违规数:", FAIL, "→", "引擎检查全部通过" if FAIL == 0 else "有问题，需排查")
if SKIP:
    print("未执行数:", SKIP, "→ **有格子的判据压根没跑**（夹具/前提没造出来）")
    print("           这一条不是通过：上面每一行「未执行」都要有人去查为什么造不出夹具。")
if FONT_GAPS:
    print("字体覆盖:", "查不了（不算通过）" if FONT_GAPS < 0 else "%d 个字符画不出来" % FONT_GAPS,
          "→ 出图会静默出方框")
sys.exit(1 if (FAIL or FONT_GAPS or SKIP) else 0)
