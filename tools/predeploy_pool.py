#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""predeploy 的 Python 那半：按并行池跑条目，每条的输出和退出码落到目录里，predeploy.sh 再**按原顺序**读回去分类、记表。
（card-b71b1600-253，Nova 10-08 20:39 点头：整门 16 分钟，Python 那半串着跑约 964 秒。）

    python3 tools/predeploy_pool.py --dir D --jobs 4 [--python PY] -- 条目1 条目2 …
    ⇒ D/<i>.log  第 i 条的 stdout+stderr
       D/<i>.rc   第 i 条的退出码
       D/<i>.sec  第 i 条的用时（秒）

排法：
  · **速度门（speed_gate.py）不进池子**：池子跑完、机器空下来以后再一条一条串着跑 —— 它量的就是时间，跟别的挤在一起会假红；
  · 池子里长的先发（LONG_FIRST，按 10-08 逐条计时的顺序）；check_abuse 两条排在**最后**：它 ⑨ 判「过期请求 <100ms」是真时间，
    池子最挤的时候别让它赶上；
  · 其余照原顺序。--jobs 1 ＝ 跟原来一模一样，一条一条按原顺序串着跑（对拍用）。
不管怎么排，读回去的顺序、分类、表格都跟原来一样 —— 排的只是**什么时候跑**。
"""
import os
import shlex
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 10-08 逐条计时（串着跑、机器空）里最长的几条，长的先发（秒数只是排序用的参考，不判）
LONG_FIRST = [
    "tools/seg_prefix_check.py",          # 306（切片前）
    "tools/selfcheck.py",                 # 119
    "web/check_parity.py --self-test",    # 60
    "tools/live_seg_check.py",            # 48（联网）
    "notes/pine-incremental-seg.py --tail 60",   # 48
    "web/check_parity.py",                # 37
    "tools/j19_check.py --self-test",     # 22
    "tools/j18_check.py --self-test",     # 19
    "tools/trend_check.py --self-test",   # 15
]
LAST_IN_POOL = ("web/check_abuse.py",)    # 真时间判据，排在池子末尾
SERIAL_AFTER = ("tools/speed_gate.py",)   # 不进池子，最后单独串着跑


def run_one(py, i, chk, d):
    t0 = time.time()
    with open(os.path.join(d, "%d.log" % i), "wb") as f:
        rc = subprocess.call([py] + shlex.split(chk), stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)
    open(os.path.join(d, "%d.rc" % i), "w").write(str(rc))
    open(os.path.join(d, "%d.sec" % i), "w").write("%d" % round(time.time() - t0))


def main(argv):
    jobs, d, py = 4, None, sys.executable
    if "--" not in argv:
        print("用法：predeploy_pool.py --dir D --jobs N [--python PY] -- 条目…", file=sys.stderr)
        return 2
    k = argv.index("--")
    opts, checks = argv[:k], argv[k + 1:]
    it = iter(opts)
    for a in it:
        if a == "--jobs":
            jobs = int(next(it))
        elif a == "--dir":
            d = next(it)
        elif a == "--python":
            py = next(it)
        else:
            print("不认识的参数：%s" % a, file=sys.stderr)
            return 2
    if not d:
        return 2
    os.makedirs(d, exist_ok=True)
    idx = list(range(len(checks)))
    if jobs <= 1:
        for i in idx:
            run_one(py, i, checks[i], d)
        return 0
    serial = [i for i in idx if checks[i].split()[0] in SERIAL_AFTER]
    pool = [i for i in idx if i not in serial]
    rank = {c: r for r, c in enumerate(LONG_FIRST)}
    pool.sort(key=lambda i: (checks[i].split()[0] in LAST_IN_POOL, rank.get(checks[i], len(rank)), i))
    queue = list(pool)
    lock = threading.Lock()

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                i = queue.pop(0)
            run_one(py, i, checks[i], d)

    ths = [threading.Thread(target=worker) for _ in range(min(jobs, len(pool)) or 1)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    for i in serial:
        run_one(py, i, checks[i], d)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
