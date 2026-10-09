#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「最后几条线段还可能挪」只有一个数，却写在两处（Nova 10-09 15:29）：
    web/withdrawn.py         PENDING_SEGS      —— 网页 segs_std 的 state、「已撤回」账本都读它
    tradingview/chanlun.pine STD_PENDING_SEGS  —— TradingView 最后几条画点线
两边不等 ⇒ 网页跟 TradingView 画的虚线条数不一样（小栋要是选 A，漏改一处就是这样）。

    python3 tools/pending_sync_check.py              # rc=0 相等 ／ 1 不等或读不到
    python3 tools/pending_sync_check.py --self-test  # 反向臂：只改一边（各试一次）必须红；红不了 ⇒ rc=3
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, "web", "withdrawn.py")
PINE = os.path.join(ROOT, "tradingview", "chanlun.pine")
PY_RE = re.compile(r"^PENDING_SEGS\s*=\s*(\d+)\b", re.M)
PINE_RE = re.compile(r"^STD_PENDING_SEGS\s*=\s*(\d+)\b", re.M)


def read(path, rx):
    """→ 那个数（int）；没有、或者顶层赋值不止一处 ⇒ None（读不准不算相等）。"""
    hits = rx.findall(open(path, encoding="utf-8").read())
    return int(hits[0]) if len(hits) == 1 else None


def check(py_text=None, pine_text=None, quiet=False):
    a = int(PY_RE.findall(py_text)[0]) if py_text is not None and len(PY_RE.findall(py_text)) == 1 else \
        (read(PY, PY_RE) if py_text is None else None)
    b = int(PINE_RE.findall(pine_text)[0]) if pine_text is not None and len(PINE_RE.findall(pine_text)) == 1 else \
        (read(PINE, PINE_RE) if pine_text is None else None)
    ok = a is not None and b is not None and a == b
    if not quiet:
        print("%s web/withdrawn.py PENDING_SEGS = %s ／ chanlun.pine STD_PENDING_SEGS = %s" % ("✓" if ok else "✗", a, b))
    return ok


def self_test():
    py = open(PY, encoding="utf-8").read()
    pine = open(PINE, encoding="utf-8").read()
    if not check(py, pine, quiet=True):
        print("✗ 原样就不相等，反向臂没意义")
        return 1
    bump = lambda rx, text: rx.sub(lambda m: m.group(0).replace(m.group(1), str(int(m.group(1)) + 1)), text, count=1)
    arms = [("只改 Python 那边（+1）", bump(PY_RE, py), pine),
            ("只改 Pine 那边（+1）", py, bump(PINE_RE, pine)),
            ("Python 那边多写一处", py + "\nPENDING_SEGS = 2\n", pine)]
    rc = 0
    for name, p, q in arms:
        red = not check(p, q, quiet=True)
        print("%s 变异「%s」⇒ %s" % ("✓" if red else "✗", name, "红" if red else "没红"))
        rc |= 0 if red else 3
    return rc


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (0 if check() else 1))
