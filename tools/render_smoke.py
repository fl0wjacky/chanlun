#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出图冒烟（card-bb93e074-3c6，Nova 10-09 00:39）：weak 下线那次，render/full_common.py 还在读 s["weak"]，
selfcheck 和整门都没走到出图这条路，是 Iris 手跑才逮到的 KeyError。这一格拿 zec15 跑一次 chart_full_smooth.render，
不炸、写得出一张非空 PNG 就算绿；图写到临时目录，不进仓库。

    python3 tools/render_smoke.py              # rc=0 才算过
    python3 tools/render_smoke.py --self-test  # 让引擎的买卖点少一个出图要读的字段（confirmed）⇒ 主跑必须红（rc=0 ＝ 红了）
"""
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, os.path.join(ROOT, "render")]


def main(quiet=False):
    say = (lambda *a: None) if quiet else print
    import render.chart_full_smooth as C
    with tempfile.TemporaryDirectory() as d:
        C.out = lambda n: os.path.join(d, os.path.basename(n))
        try:
            C.render("zec15.json", "ZEC", "15 分钟", 2, 1200)
        except Exception:
            say("✗ chart_full_smooth.render(zec15) 炸了：\n" + traceback.format_exc(limit=3))
            return 1
        png = [f for f in os.listdir(d) if f.endswith(".png")]
        size = sum(os.path.getsize(os.path.join(d, f)) for f in png)
        ok = bool(png) and size > 0
        say("%s chart_full_smooth.render(zec15) 出图 %d 张、%d 字节" % ("✓" if ok else "✗", len(png), size))
        return 0 if ok else 1


def self_test():
    import core.signals                            # noqa: F401（core 包把 signals 这个名字换成了函数，模块得从 sys.modules 拿）
    CS = sys.modules["core.signals"]
    real = CS.signals

    def drop(*a, **k):
        return [{f: v for f, v in s.items() if f != "confirmed"} for s in real(*a, **k)]

    CS.signals = drop
    try:
        rc = main(quiet=True)
    finally:
        CS.signals = real
    print("%s 臂：买卖点少了 confirmed 字段 ⇒ %s" % ("✓" if rc else "✗", "红" if rc else "没红（尺子没牙）"))
    return 0 if rc else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
