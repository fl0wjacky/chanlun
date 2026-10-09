#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pine 跟甲（S-13 甲，SEG_FINAL_PENS，小栋 10-09 Q-6b「留甲」）：逐根同步那一层的镜像，跟引擎逐前缀对账。

要回答的唯一问题：
    chanlun.pine 里 zSegStep 改成「扫 segPens(pens) 视图（不含最后一笔）」以后，**每一根 K 线**上
    A 模式拼出来的线段，跟引擎 analyze()（甲开）在同一个 K 线前缀上的线段是不是一样？

镜像的是 Pine 那几行（行号见 chanlun.pine）：
    · 同步：尾部三格签名（笔数、最后三个端点）。纯追加 ⇒ push 一笔续扫；其它 ⇒ 整段重算（清空、从头喂）。
    · 续扫喂的是视图：pens 纯追加一笔 ⇒ 视图多出来的是**上一根的最后一笔**（现在定稿了）。
    · islast：已确认段 ＋ 暂定 ＋ live 尾巴，都在视图上拼（tailFrom 到 sp.size()-1）。
笔用引擎在同一前缀上的 pens（笔层的增量另有 notes/pine-incremental-pen.py 守）；增量扫描器借 pine-incremental-seg.py
的 IncSegments（它已逐前缀证过跟 build_segments 一样）。这里只多证「视图 ＋ 同步」这一层没接错。

★ 证不了 Pine 本身（这台机器上编译不了、跑不了）；Pine 照这个形状写的那几行要人逐行核。

    python3 notes/pine-jia-parity.py               # data/ 里几份真实数据、每个笔端点前缀
    python3 notes/pine-jia-parity.py --self-test   # 反向臂：视图忘了去掉最后一笔（喂全部笔）⇒ 必须红
退出码：0 全对；1 有分歧；3 自检没红
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import core                                                          # noqa: E402,F401
from config import tick_of                                           # noqa: E402

A = sys.modules["core.analyze"]                                      # ★ 别写 import core.analyze as A：拿到的是函数
_spec = importlib.util.spec_from_file_location("pis", os.path.join(HERE, "pine-incremental-seg.py"))
PIS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PIS)

FILES = ["zec_1h.json", "zec_2h.json", "zec_4h.json", "btc_4h.json", "aaplusdt_1h.json", "aaplusdt_4h.json"]
VIEW_DROP_LAST = True                                                # 自检把它关掉 ⇒ 视图 = 全部笔


def view(pens):
    """Pine segPens()：甲开且多于一笔 ⇒ 去掉最后一笔。"""
    return pens[:-1] if VIEW_DROP_LAST and len(pens) > 1 else pens


def key(p):
    return (p["i0"], p["i1"])


def run(quiet=False):
    bad = 0
    for fn in FILES:
        bars = json.load(open(os.path.join(ROOT, "data", fn)))
        bars = bars["bars"] if isinstance(bars, dict) else bars
        tick = tick_of(fn)
        full = A.analyze(bars, tick=tick)
        cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
        inc, sig, fed, n_chk, n_rebuild = None, None, 0, 0, 0
        for c in cuts:
            r = A.analyze(bars[:c], tick=tick)
            pens = r["pens"]
            # Pine zSegStep 的签名：端点序列（seq）的长度 ＋ 最后三个端点 e1、e2、e3（e1 最后）
            ep = ([pens[0]["i0"]] if pens else []) + [p["i1"] for p in pens]
            s = (len(ep), ep[-1] if ep else -1, ep[-2] if len(ep) >= 2 else -1, ep[-3] if len(ep) >= 3 else -1)
            # 纯追加（Pine：penCount == pens.size() + 1 and e2 == sig[0] and e3 == sig[1]）
            pure = sig is not None and s[0] == sig[0] + 1 and s[2] == sig[1] and s[3] == sig[2]
            same = sig is not None and s == sig                     # 签名没动 ⇒ Pine 整个 if 不进，什么都不做
            if same:
                pass
            elif inc is None or not pure:                           # 整段重算：清空、视图从头喂
                inc, fed = PIS.IncSegments(), 0
                n_rebuild += 1
            v = view(pens)
            while fed < len(v):                                     # 纯追加：只喂视图新多出来的那几格
                inc.feed(v[fed])
                fed += 1
            sig = s
            got = [(x["PI0"], x["PI1"], bool(x.get("live"))) for x in inc.result()]
            want = [(x["PI0"], x["PI1"], bool(x.get("live"))) for x in r["segs"]]
            n_chk += 1
            if got != want:
                bad += 1
                if not quiet:
                    print("✗ %s 前缀 %d：镜像 %s ≠ 引擎 %s" % (fn, c, got[-3:], want[-3:]))
                break
        if not quiet:
            print("%s %s：%d 个前缀（整段重算 %d 次）" % ("✓" if not bad else "·", fn, n_chk, n_rebuild))
    if not quiet:
        print("全对" if not bad else "%d 份有分歧" % bad)
    return bad


def self_test():
    global VIEW_DROP_LAST
    VIEW_DROP_LAST = False
    try:
        n = run(quiet=True)
    finally:
        VIEW_DROP_LAST = True
    print("%s 变异「视图喂全部笔（忘了甲）」⇒ %d 份分歧" % ("✓" if n else "✗", n))
    return 0 if n else 3


if __name__ == "__main__":
    if not A.SEG_FINAL_PENS:
        print("✗ 引擎甲没开（core/analyze.py SEG_FINAL_PENS）")
        sys.exit(1)
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (1 if run() else 0))
