#!/usr/bin/env python3
"""往左加载：相邻两档在**重叠区间**里结构变没变 —— 卡 `card-d38154a0-e2d` 的接口那半张。

为什么要有它：前端那半张只能保证「**位置**不跳」（换完数据按时间放回原位，尺 ⑥ ＋ 浏览器工装都绿）。
但用户屏幕上还有**结构**：笔、线段、中枢、买卖点。往前补一倍数据，后台是**整份重算**的 ——
重算之后，用户正在看的那一段如果结构变了，画面照样「跳」（只是这次跳的不是位置，是画的内容）。
假 payload 量不出这一条（它是我们自己编的，编的当然自洽），只有**真接口**的一对响应量得了
（Atlas 2026-10-04 点的那句：「量的是相邻两档在重叠区间里结构变化传到哪一根」）。

判据（一句话）：**上一份的后半段，在补过数据之后必须逐条一模一样。**
  为什么是「后半段」：往前补数据，动得了的本来就只有**最左边那一截**（缠论的线段划分是确认了就不回溯的，
  真会变的只有贴着数据头的那几个「还在走」的结构）。所以：
    左半段变了 → 正常，报个深度（从右往左数，第一处不一致在第几根）；
    右半段变了 → **红灯**：用户眼皮子底下那一块被后台悄悄改了。
  「深度」那个数是给人看的：它应该远小于「最大结构跨度」，否则说明重算在往回啃。

跑法（三选一）：
    # 1) 真接口：拉相邻两档各一次（Bram 的 /api/chart 支持 span 之后才跑得起来）
    python3 tools/web_span_overlap.py --url https://<站> --symbol BTCUSDT --tf 1h --span 1 --span2 2
    # 2) 手上有一对响应（离线对账 / 别人贴过来的）
    python3 tools/web_span_overlap.py --pair old.json new.json
    # 3) 自检：拿仓里真样本编一对，验「该绿的绿、该红的红」
    python3 tools/web_span_overlap.py --selftest

★ 它**不是第七把尺**：尺子是「抠出仓里的纯函数、谁跑都一样」；这一支要一对真响应，仓里没有这样的对子。
  跟 `tools/web_more_e2e.js` 一样属于「要外部条件、但别人得能复跑」的那一类。
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(R, "web/fixtures/zec_1h.json")

RED, GREEN, DIM, OFF = "\033[31m", "\033[32m", "\033[2m", "\033[0m"

# 每一层：怎么从一条结构里取出「时间跨度」和「内容」。★ 字段名是契约的一部分，改形状就改这里；
# 抠不到字段就**抛**（不许静默比了个空）。下标字段说的是**bars 下标**（不是笔下标）。
LAYERS = [
    ("笔",     "pens",        ("i0", "i1"), ("p0", "p1")),
    ("线段",   "segs",        ("i0", "i1"), ("p0", "p1", "dir")),
    ("笔中枢", "centers",     ("X0", "X1"), ("ZD", "ZG", "DD", "GG")),
    ("线段中枢", "seg_centers", ("X0", "X1"), ("ZD", "ZG", "DD", "GG")),
]
SIG = ("signals", "bar", ("kind", "price"))


def _num(x):
    """数比到小数点后 4 位：浮点尾巴不算「结构变了」（后台换一份 JSON 也可能多抖一位）。
    不是数的字段（`dir: 'up'`、`kind: '三买'`）原样留着 —— 那些同样是结构的一部分。"""
    if x is None:
        return None
    try:
        return round(float(x), 4)
    except (TypeError, ValueError):
        return x


def times_of(d):
    return [b["t"] for b in d["bars"]]


def identity(d, tindex, items_key, idx, vals, it):
    """一条结构 → (起点时间, 终点时间, 内容...)。时间而不是下标：两档的下标一定不同。"""
    for k in list(idx) + list(vals):
        if k not in it:
            raise SystemExit("✗ 这一份里 %s 的字段 %r 不见了 —— 形状变了，别当绿" % (items_key, k))
    t0, t1 = tindex[it[idx[0]]], tindex[it[idx[1]]]
    return (t0, t1) + tuple(_num(it[v]) for v in vals)


def collect(d, items_key, idx, vals, depth=0):
    """→ {身份: 出现次数}。★ 用**多重集**：同一条结构重复出现两次也是差别（丢了一条就少一次）。"""
    if items_key == SIG[0]:
        out = {}
        for s in d.get("signals", {}).get("seg", []) + d.get("signals", {}).get("pen", []):
            if "bar" not in s:
                raise SystemExit("✗ 买卖点里没有 bar 字段 —— 形状变了，别当绿")
            key = (d["bars"][s["bar"]]["t"], d["bars"][s["bar"]]["t"]) + \
                  tuple(_num(s[v]) if v != "kind" else s[v] for v in ("kind", "price"))
            out[key] = out.get(key, 0) + 1
        return out
    tindex = times_of(d)
    out = {}
    for it in d.get(items_key) or []:
        key = identity(d, tindex, items_key, idx, vals, it)
        out[key] = out.get(key, 0) + 1
    return out


def bars_diff(old, new):
    """同一根 K 线（按时间对齐）的开高低收必须一样 —— 补更早的数据不该**改写**已有的 K 线。

    ★ 例外：**还在走的那一根**。两份响应是前后两次请求拿的，中间隔着几秒，最后那根的收盘自己在动
      （第一次跑就撞上了：ZEC 4h 最后一根 c 1319.73 → 1319.57，一分钟之内的事）—— 那不是改写，
      是行情在走。契约里 `closed: false` 说的就是它，所以照它跳过，并且**说出来**跳了哪一根，
      不许静默放过（不然这条判据会被一根永远在动的 K 线变成永远的红，红久了就没人看了）。
    """
    live = set()
    for d in (old, new):
        if not d.get("closed", True) and d.get("bars"):
            live.add(d["bars"][-1]["t"])
    by_t = {b["t"]: b for b in new["bars"]}
    bad, skipped = [], []
    for b in old["bars"]:
        if b["t"] in live:
            skipped.append(b["t"])
            continue
        n = by_t.get(b["t"])
        if n is None:
            bad.append((b["t"], "新的一份里没有这根"))
            continue
        for f in ("o", "h", "l", "c"):
            if _num(b[f]) != _num(n.get(f)):
                bad.append((b["t"], "%s %s → %s" % (f, b[f], n.get(f))))
                break
    return bad, skipped


def compare(old, new):
    """→ (每层明细, 判据行, 跳过的活 K 线)。判据行里第一项是判据名，方便红在对的地方。"""
    to, tn = times_of(old), times_of(new)
    if not to or not tn:
        raise SystemExit("✗ 有一份没有 bars")
    if to[0] not in set(tn):
        raise SystemExit("✗ 两份对不上：老那份的头一根 %s 不在新那份里（不是同一段数据？）" % to[0])
    if tn[0] >= to[0]:
        raise SystemExit("✗ 两份对不上：新的那份没有更早的数据（span 是同一个？）")
    overlap = [t for t in to if t in set(tn)]
    mid = overlap[len(overlap) // 2]              # 「后半段」＝重叠区中位时间之后
    rows, bad = [], []
    for name, key, idx, vals in LAYERS:
        o, n = collect(old, key, idx, vals), collect(new, key, idx, vals)
        # ★ 对称比：老的有、新的没有，和老没有、新的多出来一条，**都是差别** ——
        #   只遍历老的那些键，会漏掉「重算之后多长出一段结构」这一种（那同样是用户眼里的画面变了）。
        keys = set(k for k in o if k[0] >= overlap[0]) | set(k for k in n if k[0] >= overlap[0])
        deep = [k for k in keys if o.get(k, 0) != n.get(k, 0)]
        depth = 0 if not deep else sum(1 for t in overlap if t > max(k[1] for k in deep))
        right = [k for k in deep if k[1] >= mid]
        rows.append({"层": name, "条数(老)": sum(o.values()), "差异": len(deep), "深度": depth,
                     "右半段的差异": len(right), "最早一处": min((k[0] for k in deep), default=None),
                     "最右一处": max((k[1] for k in deep), default=None)})
        if right:
            bad.append(("②结构", "%s 在右半段变了" % name,
                        "%d 条（最右一处 %s）" % (len(right), _iso(max(k[1] for k in right))),
                        "右半段逐条一模一样",
                        "用户眼皮子底下那一块被重算改了 —— 位置没跳，画的内容跳了"))
    o, n = collect(old, SIG[0], SIG[1], SIG[2]), collect(new, SIG[0], SIG[1], SIG[2])
    skeys = set(k for k in o if k[0] >= overlap[0]) | set(k for k in n if k[0] >= overlap[0])
    sdeep = [k for k in skeys if o.get(k, 0) != n.get(k, 0)]
    sright = [k for k in sdeep if k[1] >= mid]
    rows.append({"层": "买卖点", "条数(老)": sum(o.values()), "差异": len(sdeep),
                 "深度": 0 if not sdeep else sum(1 for t in overlap if t > max(k[1] for k in sdeep)),
                 "右半段的差异": len(sright), "最早一处": min((k[0] for k in sdeep), default=None),
                 "最右一处": max((k[1] for k in sdeep), default=None)})
    if sright:
        bad.append(("②结构", "买卖点在右半段变了", "%d 个" % len(sright), "一个都不许动",
                    "屏幕上那一排三角是用户照着做决定的"))
    bad_bars, skipped = bars_diff(old, new)
    for t, why in bad_bars:
        where = "右半段" if t >= mid else "左半段"
        bad.append(("①数据", "同一根 K 线对不上（%s）" % where, "%s：%s" % (_iso(t), why),
                    "按时间对齐后完全一样", "补更早的数据不该改写已有的 K 线"))
    return rows, bad, skipped


def _iso(ms):
    import datetime
    # 币安的 t 是 UTC 毫秒：显式带 tz 再格式化，别用 utcfromtimestamp（3.12 起弃用，跑起来还往 stderr
    # 吐一行 DeprecationWarning —— 这工具的输出是给人看的，混一行警告进去就是噪声）。
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")


def fetch(base, symbol, tf, span):
    q = urllib.parse.urlencode({"symbol": symbol, "tf": tf, "span": span})
    url = base.rstrip("/") + "/api/chart?" + q
    # ★ 站点会拦掉没有 UA 的请求（403）—— 拿 curl 试得通、拿 urllib 试不通，就是这个原因。
    req = urllib.request.Request(url, headers={"User-Agent": "chanlun-span-overlap/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        hint = ("　⇒ 后台还不认 span（契约是 1/2/4/8/16 那五个值）—— Bram 那半张还没上，"
                "这一趟量不了结构，**别当绿也别当红**" if e.code == 400 else "")
        raise SystemExit("✗ %s 回了 HTTP %s%s" % (url, e.code, hint))
    if not d.get("bars"):
        raise SystemExit("✗ %s 没回 bars" % url)
    if "span" not in d:
        raise SystemExit("✗ %s 的响应里没有 span 字段 —— 后台还没接契约，这一趟量不了结构" % url)
    if d.get("span") != span:
        print("%s· 后台把档钳了：要 %s、回 %s（按回显比对）%s" % (DIM, span, d.get("span"), OFF))
    return d


def report(old, new, label=""):
    rows, bad, skipped = compare(old, new)
    print("重叠区间结构对账%s：老 %s 根（%s → %s）／新 %s 根（%s → …）"
          % (label, len(old["bars"]), _iso(old["bars"][0]["t"]), _iso(old["bars"][-1]["t"]),
             len(new["bars"]), _iso(new["bars"][0]["t"])))
    print("  判据：老那份**后半段**的结构与买卖点，必须逐条一模一样（位置不跳是前端那半张的账）")
    print("  「右边未动」＝最深一处差异的**右边**还有多少根没被动过（应该远大于 0：说明重算没往回啃）\n")
    for r in rows:
        mark = "✓" if not r["右半段的差异"] else "✗"
        # 一条差异都没有时，「右边未动 0 根」读起来像坏消息 —— 那一格是空的，就印「—」。
        dep = "—" if not r["差异"] else "%d 根" % r["深度"]
        print("   %s %-8s 老 %4d 条 · 差异 %3d 条 · 右边未动 %6s · 右半段 %d 条%s"
              % (mark, r["层"], r["条数(老)"], r["差异"], dep, r["右半段的差异"],
                 "" if not r["差异"] else "（最早一处 %s）" % _iso(r["最早一处"])))
    if skipped:
        print("   %s（跳过还在走的那根 %s：两份是前后两次请求，它在自己动）%s"
              % (DIM, "、".join(_iso(t) for t in skipped), OFF))
    if bad:
        print("\n%s✗ %d 处不对：%s" % (RED, len(bad), OFF))
        for j, case, g, w, why in bad:
            print("   %s✗%s [%s] %s：实际 %s ≠ 期望 %s ← %s" % (RED, OFF, j, case, g, w, why))
        return 1
    print("\n%s✓%s 重叠区间里的**后半段**结构逐条一致（差异只在最左边那一截，「右边未动」那一列见上）"
          % (GREEN, OFF))
    return 0


# ---------- 自检：拿仓里真样本编一对，两个方向都要对 ----------

def fabricate(n=2016, perturb=None):
    """老那份 ＝ 真样本切掉头 n 根；新那份 ＝ 编的 n 根更早的 K 线 ＋ 真样本，结构整体平移。
    ★ 编出来的 K 线**不许等距重复**（尺 ⑥ 那条账）：这里虽然只比结构不比像素，也照样摆动，
      免得哪天有人拿这一对去量位置，量出个假绿。"""
    import math
    full = json.load(open(FIXTURE, encoding="utf-8"))
    # ★ 这份 bars 必须**拷一份**再用：直接拿 fixture 的 dict 去拼旧新两份，两边就是同一批对象 ——
    #   探针改一根 K 线会同时改到两份，对账对出来「一模一样」（假绿）。这一条是被自检逮出来的。
    bars = json.loads(json.dumps(full["bars"]))
    step = bars[1]["t"] - bars[0]["t"]
    head = bars[0]
    older = []
    for i in range(n, 0, -1):
        w = math.sin(i / 7.3) * 0.0022 + math.sin(i / 31.7) * 0.0011
        c, o = head["c"] * (1 + w), head["o"] * (1 + w * 0.93)
        older.append({"t": head["t"] - i * step, "o": o, "h": max(o, c) * 1.0009,
                      "l": min(o, c) * 0.9991, "c": c})
    new = json.loads(json.dumps(full))
    new["bars"] = older + bars
    new["nbars"] = len(new["bars"])
    for key in list(new.keys()):
        for it in new[key] if isinstance(new.get(key), list) else []:
            for f in ("i0", "i1", "X0", "X1", "F1", "x0", "x1"):
                if f in it:
                    it[f] += n
    for k in ("seg", "pen"):
        for s in new.get("signals", {}).get(k, []):
            s["bar"] += n
    old = json.loads(json.dumps(full))
    # ★ 旧新两份**不许共用同一批 bar 对象**（上面那处拷贝只解决了一半）：共用的话，探针在「新那份」上
    #   改一根 K 线会连「老那份」一起改，对账对出来一模一样 —— 又一格假绿。
    old["bars"] = json.loads(json.dumps(bars[n // 2:]))
    old["nbars"] = len(old["bars"])
    # 老那份是「手上那份」：它自己的下标也要跟着切掉的那一半往前挪
    cut = n // 2
    for key in list(old.keys()):
        for it in old[key] if isinstance(old.get(key), list) else []:
            for f in ("i0", "i1", "X0", "X1", "F1", "x0", "x1"):
                if f in it:
                    it[f] = max(0, it[f] - cut)
            if "i0" in it and it["i0"] >= it["i1"]:
                it["i0"] = max(0, it["i1"] - 1)
    old["pens"] = [p for p in old["pens"] if p["i1"] > 0]
    old["segs"] = [s for s in old["segs"] if s["i1"] > 0]
    old["centers"] = [c for c in old["centers"] if c["X1"] > 0]
    old["seg_centers"] = [c for c in old["seg_centers"] if c["X1"] > 0]
    for k in ("seg", "pen"):
        old["signals"][k] = [dict(s, bar=s["bar"] - cut) for s in old["signals"][k] if s["bar"] >= cut]
    if perturb:
        perturb(old, new, cut)
    return old, new


def selftest():
    cases = []

    def run(name, fn, want_red):
        old, new = fabricate(perturb=fn)
        _, bad, _ = compare(old, new)
        red = bool(bad)
        cases.append((name, red == want_red, "%d 处红" % len(bad), "红" if want_red else "绿"))

    run("基准：只把老 K 线接在头上、结构整体平移 ⇒ 必须绿", None, False)
    # ★ 探针要**打在右半段上**：老那份＝真样本切掉头一半，所以它的右半段＝真数据靠后那一段。
    #   第一版打在「中间那条笔」上，其实落在了左半段 —— 该绿的地方绿了，探针是空转的。
    run("右半段改一条笔的价 ⇒ 必须红",
        lambda o, n, c: n["pens"][-2].__setitem__("p1", n["pens"][-2]["p1"] * 1.01), True)
    run("右半段多长出一条笔（老那份没有）⇒ 必须红",
        lambda o, n, c: n["pens"].append(dict(n["pens"][-1], p1=n["pens"][-1]["p1"] * 1.03)), True)
    run("右半段丢一个买卖点 ⇒ 必须红",
        lambda o, n, c: n["signals"]["pen"].pop(len(n["signals"]["pen"]) - 1), True)
    run("右半段线段方向反了 ⇒ 必须红",
        lambda o, n, c: n["segs"][len(n["segs"]) - 2].__setitem__("dir", "down"), True)
    run("右半段某根 K 线的收盘被改写 ⇒ 必须红",
        lambda o, n, c: n["bars"][len(n["bars"]) - 50].__setitem__("c", n["bars"][len(n["bars"]) - 50]["c"] * 1.02), True)

    # ★ 这一对是**活 K 线**那条豁免的两端：正在走的那根（`closed: false`）两份对不上是**正常**的
    #   （两次请求隔了几秒，它自己在动），要是照样红，这条判据就变成「永远的红」—— 红久了没人看。
    #   反过来，`closed: true` 的最后一根被改写就是真事，必须红。
    def live_last(o, n, c):
        o["closed"] = n["closed"] = False
        n["bars"][-1]["c"] = n["bars"][-1]["c"] * 1.02
        o["bars"][-1]["c"] = o["bars"][-1]["c"] * 1.01

    def closed_last(o, n, c):
        n["bars"][-1]["c"] = n["bars"][-1]["c"] * 1.02

    run("正在走的那根（closed=false）两份不一样 ⇒ 必须**绿**（跳过它）", live_last, False)
    run("已收盘的最后一根被改写（closed=true）⇒ 必须红", closed_last, True)
    # ★ 这条是**反向**的：最左边那一截本来就该变（补进来的老 K 线自己会长出结构）
    #   工具要是「看见差异就红」，它量的是「有没有差异」而不是「右半段动没动」。
    run("只有最左边一截变了（老那份的头几条笔）⇒ 必须**绿**",
        lambda o, n, c: n["pens"][0].__setitem__("p1", n["pens"][0]["p1"] * 1.01), False)
    ok = True
    for name, hit, why, _ in cases:
        ok &= hit
        print("%s 自检「%s」：%s" % (GREEN + "✓" + OFF if hit else RED + "✗" + OFF, name, why))
    print("%s 自检：%d/%d 格（含一条反向：最小值那截该变就得让它变）"
          % (GREEN + "✓" + OFF if ok else RED + "✗" + OFF, sum(1 for c in cases if c[1]), len(cases)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="站根地址（真接口那一趟）")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--span", type=int, default=1)
    ap.add_argument("--span2", type=int, default=2)
    ap.add_argument("--pair", nargs=2, metavar=("OLD", "NEW"), help="两份响应文件（离线对账）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    if a.pair:
        old = json.load(open(a.pair[0], encoding="utf-8"))
        new = json.load(open(a.pair[1], encoding="utf-8"))
        raise SystemExit(report(old, new, "（%s ↔ %s）" % (os.path.basename(a.pair[0]), os.path.basename(a.pair[1]))))
    if a.url:
        print("拉 %s %s span=%d / span=%d …" % (a.symbol, a.tf, a.span, a.span2))
        old = fetch(a.url, a.symbol, a.tf, a.span)
        new = fetch(a.url, a.symbol, a.tf, a.span2)
        raise SystemExit(report(old, new, "（span=%s ↔ span=%s）" % (old.get("span"), new.get("span"))))
    ap.error("要 --url ＋ --span/--span2，或 --pair，或 --selftest")


if __name__ == "__main__":
    main()
