#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上线门：对线上那 15 张图（SYMBOLS × TFS，span=1）现拉现算，跑线段层 check_segments，报错就拦（Nova 10-06，card-acbe5855）。

    python3 tools/live_seg_check.py          # rc=0 全过 ／ 1 有图报错（已知例外除外）／ 2 拉不到数据，没比成

为什么要它：夹具是冻结的，线上窗口每天在滚；线段层的毛病可能只在今天的线上数据上露出来
（10-06 线上 AAPL 1h／2h 第一段「顶不高于底」，夹具里没有）。
已知例外（KNOWN）照印、不拦；那张卡修好以后把例外删掉 —— 例外那张图如果已经干净了，这里会提醒删。
数据走 web/server.py 自己的 get_chart（跟线上同一条路：同一窗口、同一 tick），所以量的就是线上发出去的那份。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web"))
sys.path.insert(0, HERE)
import server                                                 # noqa: E402
from core.segment import check_segments                       # noqa: E402

# 已知例外：(品种, 周期) → 卡号。修好就删。
KNOWN = {("AAPLUSDT", "1h"): "card-24dd71cb-003", ("AAPLUSDT", "2h"): "card-24dd71cb-003"}


def main():
    bad = skipped = 0
    for sym in server.SYMBOLS:
        for tf in server.TFS:
            try:
                got = server.get_chart(sym, tf, span=1, prefetch=False)   # → (json bytes, gzip bytes) 或 None
                d = json.loads(got[0])
                segs, pens = d["segs"], d["pens"]
            except Exception as e:                            # 拉不到 / 形状不对：没比成，不当绿
                print("· %s %s 没比成：%s" % (sym, tf, str(e)[:80]))
                skipped += 1
                continue
            um = []
            v = check_segments(segs, pens, um) + um          # 「量不了」在上线门里也拦（同 ⑧ 口径：不当绿）
            known = KNOWN.get((sym, tf))
            if v and known:
                print("~ %s %s 已知例外（%s）：%d 处，例 %s" % (sym, tf, known, len(v), v[:1]))
            elif v:
                print("✗ %s %s 线段不变量 %d 处，例 %s" % (sym, tf, len(v), v[:2]))
                bad += 1
            elif known:
                print("✓ %s %s 已经干净了 —— %s 修好了的话，把它从 KNOWN 里删掉" % (sym, tf, known))
            else:
                print("✓ %s %s（%d 段）" % (sym, tf, len(segs)))
    if bad:
        print("%d 张图线段层报错（已知例外除外）" % bad)
        return 1
    if skipped:
        print("%d 张图没比成：不算通过" % skipped)
        return 2
    print("全部通过（已知例外 %d 张照印）" % len(KNOWN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
