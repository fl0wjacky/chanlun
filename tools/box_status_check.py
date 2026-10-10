#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段框「已确认」不收回（要求六；card-900b75a1-f83，小栋 10-10 08:01 选 B）。

逐笔前缀回放（每一笔终点后一根取一次前缀、整个重算，同 tools/seg_prefix_check.py 的取法）：上一步 status=="已确认" 的线段框，
下一步必须还在（身份＝(X0, X1, ZD, ZG)）。在任何一步消失 ⇒ 红。

    python3 tools/box_status_check.py              # rc=0 一个都没消失 ／ 1 有
    python3 tools/box_status_check.py --self-test  # 反向臂：BOX_STATUS_B 关掉（框一律已确认）⇒ 必须报出消失；报不出 ⇒ rc=3

夹具只取 data/ 里四份（zec_1h、zec_2h、aaplusdt_30m、btc_4h）：25 张全量回放要十几分钟，进不了 predeploy；
这四份在旧口径下各自都有已确认框消失（25 张实测 card-900b75a1-f83：14／3／3／3），反向臂有牙。全量数在卡上。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze  # noqa: E402
import core.trend as T  # noqa: E402
from config import tick_of  # noqa: E402

FILES = ["zec_1h", "zec_2h", "aaplusdt_30m", "btc_4h"]


def gone_boxes(fn):
    bars = json.load(open(os.path.join(ROOT, "data", fn + ".json")))
    bars = bars["bars"] if isinstance(bars, dict) else bars
    t = tick_of(fn + ".json")
    cuts = sorted({p["i1"] + 1 for p in analyze(bars, tick=t)["pens"]} | {len(bars)})
    prev, bad = None, []
    for c in cuts:
        zz = T.trend_v3(analyze(bars[:c], tick=t))["seg_centers"]
        cur = {(z["X0"], z["X1"], z["ZD"], z["ZG"]) for z in zz}
        if prev is not None:
            bad += [(c, k) for k in prev - cur]
        prev = {(z["X0"], z["X1"], z["ZD"], z["ZG"]) for z in zz if z.get("status") == "已确认"}
    return bad


def run(quiet=False):
    total = 0
    for fn in FILES:
        bad = gone_boxes(fn)
        total += len(bad)
        if not quiet:
            print("%s %s：已确认框后来消失 %d%s" % ("✓" if not bad else "✗", fn, len(bad),
                                              "" if not bad else "，例：前缀 %d 框 %s" % bad[0]))
    return total


def self_test():
    T.BOX_STATUS_B = False
    try:
        n = run(quiet=True)
    finally:
        T.BOX_STATUS_B = True
    ok = n > 0
    print("%s 变异「BOX_STATUS_B 关掉（框一律已确认）」⇒ 消失 %d 个" % ("✓" if ok else "✗", n))
    return 0 if ok else 3


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    n = run()
    print("全部通过" if n == 0 else "已确认框消失 %d 个" % n)
    sys.exit(0 if n == 0 else 1)
