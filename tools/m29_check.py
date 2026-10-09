# -*- coding: utf-8 -*-
"""M29 二类判据 ＋ 小转大的二类（第四批，买卖点.md:106／109）。

主跑：data/ 10 份上，线段级、笔级的二类点各多少（照新判据），以及走势层 xzd_seconds（小转大的二类）各多少。
  不变量：① 每颗二类都带 why，且是「不创新低」「创新低＋盘整背驰」之一；② 不再出 weak 字段（10-09 第六批下线，创新低与否读 why：signals.newx）；
          ③ xzd_seconds 每颗都对着一把标了「小转大」的 D2-2 刀，位置是刀之后第二段的终点（L53「一个次级别向上、接着一个次级别向下」）。
--self-test（造出来的，真数据里眼下没有「创新低」的二类）：
  ⑴ 把 zec15 笔级一颗二买那一段压到一买下面（造创新低），盘整背驰判成不成立 ⇒ 这颗二买必须没了；判成成立 ⇒ 必须在、why＝创新低＋盘整背驰；
  ⑵ M29 开关关掉 ⇒ 那颗照旧出（why＝「创新低（未查盘整背驰）」，newx 为真，也就是原来的「弱」），证明 ⑴ 拿掉它的确实是 M29；
  ⑶ _panzheng 换成永远成立 ⇒ zec15 的 D2-5 死点类型必须变（证明 D2-5 和 M29 共用这一份判法）；
  ⑷ 小转大那一支关掉 ⇒ zec15 的 xzd_seconds 必须空；
  ⑸ 丙6 读法 B（拿掉 451.54 那一刀，照 agent/bram/c6-figs 的做法在 find_bounds 结果里拿掉）⇒ 没有小转大的二类、不报错。
"""
import sys, os, importlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]
from core.analyze import analyze_file                      # noqa: E402
S = importlib.import_module("core.signals")                # core 包把 signals 函数导出成同名，取模块要这样
T = importlib.import_module("core.trend")

DATA = ["aaplusdt_1h.json", "aaplusdt_2h.json", "aaplusdt_30m.json", "aaplusdt_4h.json", "btc_4h.json",
        "zec15.json", "zec30_cut.json", "zec_1h.json", "zec_2h.json", "zec_4h.json"]
WHY_BUY = ("不创新低", "创新低＋盘整背驰")
WHY_SELL = ("不创新高", "创新高＋盘整背驰")   # 二卖按方向写（Iris 10-08 17:07 逮到原来二卖也写「低」）
XZD_BASE = {"zec15.json": [452.0], "zec30_cut.json": [452.0]}   # 线上 ZEC 15m／30m 快照也都是 452.0（不在 data/）


def main():
    bad, tot = [], {"seg": 0, "pen": 0, "xzd": 0}
    for f in DATA:
        r = analyze_file(f)
        for lv in ("seg", "pen"):
            for s in S.signals(r, lv):
                if s["kind"] not in ("二买", "二卖"):
                    continue
                tot[lv] += 1
                if s.get("why") not in (WHY_BUY if s["kind"] == "二买" else WHY_SELL):
                    bad.append("%s %s %s bar %d 没有 why 或 why 不认识：%r" % (f, lv, s["kind"], s["bar"], s.get("why")))
                if "weak" in s:
                    bad.append("%s %s %s bar %d 还带着 weak（10-09 已下线）" % (f, lv, s["kind"], s["bar"]))
        v = T.trend_v3(r)
        bs = {b["bar"]: b for b in v["bounds"]}
        for x in v["xzd_seconds"]:
            tot["xzd"] += 1
            b = bs.get(x["from_bar"])
            done = T.find_bounds(r)["done"]
            ok = b and b.get("death") == "小转大" and b["line_seg"] + 2 < len(done) and done[b["line_seg"] + 2]["i1"] == x["bar"]
            if not ok:
                bad.append("%s xzd_seconds bar %d 不在小转大那一刀之后第二段的终点" % (f, x["bar"]))
    for f in XZD_BASE:                                      # 基线：小转大那一刀之后的双底，二买 452.0（Nova 10-08 16:26）
        got = [round(x["price"], 2) for x in T.trend_v3(analyze_file(f))["xzd_seconds"]]
        if got != XZD_BASE[f]:
            bad.append("%s 小转大的二类基线 %s，应为 %s" % (f, got, XZD_BASE[f]))
    print("data/ %d 份：二类 线段级 %d、笔级 %d；小转大的二类 %d" % (len(DATA), tot["seg"], tot["pen"], tot["xzd"]))
    for x in bad:
        print("  ✗", x)
    print("全部通过" if not bad else "违规 %d" % len(bad))
    return 1 if bad else 0


def self_test():
    miss = 0
    r0 = analyze_file("zec15.json")
    s2s = [s for s in S.signals(r0, "pen") if s["kind"] == "二买"]
    tgt = s2s[0]
    q = tgt["unit"]

    def probe(pz, m29=True):
        r = analyze_file("zec15.json")
        P = r["pens"]
        C = P[q - 2]
        P[q] = dict(P[q], p1=C["p1"] - 1.0, lo=min(P[q]["lo"], C["p1"] - 1.0))     # 造创新低
        if q + 1 < len(P):
            P[q + 1] = dict(P[q + 1], p0=P[q]["p1"], lo=min(P[q + 1]["lo"], P[q]["p1"]))
        real, real_m = S._panzheng, S._M29
        S._panzheng = (lambda *a, **k: pz) if pz is not None else real
        S._M29 = m29
        try:
            return [s for s in S.signals(r, "pen") if s["kind"] == "二买" and s["unit"] == q]
        finally:
            S._panzheng, S._M29 = real, real_m

    gone, kept, off = probe(False), probe(True), probe(False, m29=False)
    ok = (not gone and kept and kept[0].get("why") == "创新低＋盘整背驰" and S.newx(kept[0])
          and off and S.newx(off[0]) and "weak" not in off[0])
    print("%s M29 造创新低（笔 %d）：无盘整背驰 ⇒ %s；有 ⇒ %s（newx %s）；关掉 M29 ⇒ %s" % (
        "✓" if ok else "✗", q, "不出" if not gone else "还在（牙没咬到）",
        (kept[0].get("why") if kept else "没了（误删）"), bool(kept and S.newx(kept[0])),
        ("照旧出、why＝%s、newx 真" % off[0].get("why")) if off and S.newx(off[0]) else "不对"))
    miss += not ok

    base = [b["death"] for b in T.trend_v3(r0)["bounds"]]
    real = S._panzheng
    S._panzheng = lambda *a, **k: True
    try:
        flip = [b["death"] for b in T.trend_v3(r0)["bounds"]]
    finally:
        S._panzheng = real
    ok = flip != base
    print("%s _panzheng 永远成立 ⇒ D2-5 死点类型%s（D2-5 跟 M29 共用一份判法）" % ("✓" if ok else "✗", "变了" if ok else "没变（没共用）"))
    miss += not ok

    on = T.trend_v3(r0)["xzd_seconds"]
    T._XZD_SECOND = False
    try:
        offx = T.trend_v3(r0)["xzd_seconds"]
    finally:
        T._XZD_SECOND = True
    ok = bool(on) and not offx
    print("%s 小转大的二类：照常 %d 颗（%s）；关掉 ⇒ %d 颗" % ("✓" if ok else "✗", len(on),
          ", ".join("%s %.2f" % (x["kind"], x["price"]) for x in on), len(offx)))
    miss += not ok

    # 改回「确立回抽」（D2-2 的回抽段终点，10-08 更正前的写法）⇒ 主跑必须红（30m 会回到 751.36、15m 回到 488.24）
    real_x = T._xzd_seconds
    def old_pos(done, bounds, r=None):
        out = real_x(done, bounds, r)
        for x in out:
            b = next(bb for bb in bounds if bb["bar"] == x["from_bar"])
            u = done[b["pullback_line_seg"]]
            x.update(bar=u["i1"], price=u["p1"])
        return out
    T._xzd_seconds = old_pos
    try:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            red = main()
        olds = sorted(round(x["price"], 2) for f in ("zec15.json", "zec30_cut.json") for x in T.trend_v3(analyze_file(f))["xzd_seconds"])
    finally:
        T._xzd_seconds = real_x
    ok = red == 1
    print("%s 小转大的二类改回「确立回抽」⇒ 主跑%s（那两颗变成 %s）" % ("✓" if ok else "✗", "红了" if ok else "没红（牙没咬到）", olds))
    miss += not ok

    xz = [b for b in T.trend_v3(r0)["bounds"] if b.get("death") == "小转大"]
    real_fb = T.find_bounds
    drop = {b["bar"] for b in xz}

    def fb_b(*a, **k):
        res = real_fb(*a, **k)
        keep = [i for i, b in enumerate(res["bounds"]) if b["bar"] not in drop]
        res = dict(res, bounds=[res["bounds"][i] for i in keep], ks=[res["ks"][i] for i in keep])
        return res
    T.find_bounds = fb_b
    try:
        vb = T.trend_v3(r0)
        err = None
    except Exception as e:                                  # noqa: BLE001
        vb, err = None, repr(e)
    finally:
        T.find_bounds = real_fb
    ok = err is None and not any(x["from_bar"] in drop for x in vb["xzd_seconds"]) and bool(drop)
    print("%s 丙6 读法 B（拿掉小转大那一刀 %s）⇒ %s" % ("✓" if ok else "✗", sorted(drop),
          ("报错 " + err) if err else ("小转大的二类 %d 颗" % len(vb["xzd_seconds"]))))
    miss += not ok
    print("自检全部有牙" if not miss else "自检 %d 条没咬到" % miss)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
