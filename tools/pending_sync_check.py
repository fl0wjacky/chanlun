#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「最后几条线段还可能挪」只有一个数，却写在三处（Nova 10-09 15:29；第三处 card-900b75a1-f83，小栋 10-10 08:01 选 B）：
    web/withdrawn.py         PENDING_SEGS        —— 网页 segs_std 的 state、「已撤回」账本都读它
    tradingview/chanlun.pine STD_PENDING_SEGS    —— TradingView 最后几条画点线
    core/trend.py            _BOX_PENDING_SEGS   —— 线段框「已确认」三条之一：成员线段不在最后这几条里（引擎不反向 import web）
三处不等 ⇒ 网页、TradingView、框状态三者对「哪几条线段还待定」说法不一（漏改一处就是这样）。

    python3 tools/pending_sync_check.py              # rc=0 三处相等 ／ 1 不等或读不到
    python3 tools/pending_sync_check.py --self-test  # 反向臂：只改一处（每处各试一次）、多写一处，都必须红；红不了 ⇒ rc=3
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = [
    ("web/withdrawn.py PENDING_SEGS", os.path.join(ROOT, "web", "withdrawn.py"), re.compile(r"^PENDING_SEGS\s*=\s*(\d+)\b", re.M)),
    ("chanlun.pine STD_PENDING_SEGS", os.path.join(ROOT, "tradingview", "chanlun.pine"), re.compile(r"^STD_PENDING_SEGS\s*=\s*(\d+)\b", re.M)),
    ("core/trend.py _BOX_PENDING_SEGS", os.path.join(ROOT, "core", "trend.py"), re.compile(r"^_BOX_PENDING_SEGS\s*=\s*(\d+)\b", re.M)),
]


def value(text, rx):
    """→ 那个数（int）；没有、或者顶层赋值不止一处 ⇒ None（读不准不算相等）。"""
    hits = rx.findall(text)
    return int(hits[0]) if len(hits) == 1 else None


def check(texts=None, quiet=False):
    texts = texts or [open(p, encoding="utf-8").read() for _, p, _ in PLACES]
    vals = [value(t, rx) for t, (_, _, rx) in zip(texts, PLACES)]
    ok = None not in vals and len(set(vals)) == 1
    if not quiet:
        print("%s %s" % ("✓" if ok else "✗", " ／ ".join("%s = %s" % (n, v) for (n, _, _), v in zip(PLACES, vals))))
    return ok


def self_test():
    texts = [open(p, encoding="utf-8").read() for _, p, _ in PLACES]
    if not check(texts, quiet=True):
        print("✗ 原样就不相等，反向臂没意义")
        return 1
    bump = lambda rx, text: rx.sub(lambda m: m.group(0).replace(m.group(1), str(int(m.group(1)) + 1)), text, count=1)
    arms = []
    for i, (name, _, rx) in enumerate(PLACES):
        t = list(texts); t[i] = bump(rx, t[i]); arms.append(("只改 %s（+1）" % name, t))
    t = list(texts); t[0] = t[0] + "\nPENDING_SEGS = 2\n"; arms.append(("web 那边多写一处", t))
    rc = 0
    for name, t in arms:
        red = not check(t, quiet=True)
        print("%s 变异「%s」⇒ %s" % ("✓" if red else "✗", name, "红" if red else "没红"))
        rc |= 0 if red else 3
    return rc


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (0 if check() else 1))
