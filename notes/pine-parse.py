#!/usr/bin/env python3
"""Pine 语法解析（只证明写法合法，不证明语义/编译/实时回滚）。

用法：PYTHONPATH=/tmp/pinelib python3 -u notes/pine-parse.py <file.pine>
退出码：0 = 解析通过，1 = 解析失败，2 = 环境问题（pynescript 没装上）。
慢：900 行的 chanlun.pine 要跑好几分钟（ANTLR 纯 Python）。
"""
import sys
import time

path = sys.argv[1] if len(sys.argv) > 1 else "tradingview/chanlun.pine"

try:
    from pynescript import ast as A
except Exception as e:                                    # noqa: BLE001
    print("ENVFAIL 装不上 pynescript:", type(e).__name__, e)
    sys.exit(2)

src = open(path, encoding="utf-8").read()
n = src.count("\n") + 1
print(f"解析 {path}（{n} 行）…", flush=True)

t0 = time.time()
try:
    A.parse(src)
except Exception as e:                                    # noqa: BLE001
    print(f"FAIL {type(e).__name__}  [{time.time() - t0:.0f}s]")
    print(str(e)[:4000])
    sys.exit(1)

print(f"OK 语法解析通过  [{time.time() - t0:.0f}s]")
sys.exit(0)
