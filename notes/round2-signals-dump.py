# -*- coding: utf-8 -*-
"""第二轮「背驰判法收成一块 + 补前提③」的**改前 / 改后读数**（只读，不动 core/）。

一份数据 × 两种层，逐条印出三类买卖点，再印一次自检违规。用法：

    python3 notes/round2-signals-dump.py > /tmp/before.txt     # 改 core/ 之前
    python3 notes/round2-signals-dump.py > /tmp/after.txt      # 改 core/ 之后
    diff /tmp/before.txt /tmp/after.txt

★ 六份数据的名单在这里写死（第二轮全组口径）：zec15 · zec_1h · zec_4h ·
  btc_4h · aaplusdt_4h · aaplusdt_30m —— 与引擎对说明书审计那轮用的同一份六份。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_file                      # noqa: E402
from core.signals import signals, check_signals            # noqa: E402

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]
LEVELS = ("seg", "pen")
KINDS = ("一买", "二买", "三买", "一卖", "二卖", "三卖")


def main():
    tot = {}
    for lv in LEVELS:
        for fn in FILES:
            r = analyze_file(fn)
            sig = signals(r, lv, "macd")
            bad = check_signals(sig, r, lv, "macd")
            print("== %s|%s  点 %d  自检 %d" % (fn.replace(".json", ""), lv, len(sig), len(bad)))
            for s in sig:
                print("   %-4s bar=%-7d price=%-12.4f confirmed=%-5s why=%s"
                      % (s["kind"], s["bar"], s["price"], s["confirmed"], s.get("why")))
                tot[s["kind"]] = tot.get(s["kind"], 0) + 1
            for b in bad:
                print("   !! 自检 %s" % (b,))
    print("")
    print("== 合计 ==")
    for k in KINDS:
        print("   %s %d" % (k, tot.get(k, 0)))
    print("   全部 %d" % sum(tot.values()))


if __name__ == "__main__":
    main()
