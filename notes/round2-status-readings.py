# -*- coding: utf-8 -*-
"""「改前 / 改后」读数：给每个中枢加 `status` / `status_note` 之后，六份 data/ 上到底变了什么。

用法：
    python3 notes/round2-status-readings.py            # 改前 = HEAD，改后 = 工作区
    python3 notes/round2-status-readings.py --before <sha>

两件事：
    ① **逐位对账**：把改后输出里的两个新键剥掉，必须与改前**逐位相同**（证明改动是纯增量的，
       不碰任何几何/判据字段）。不成立就红着退出。
    ② **读数表**：每份数据的 中枢数 / 仍在延续 / 终结方式分布 / 已确认·暂定 分布。

★ 两棵树分别在**子进程**里跑，避免两边的 core 互相污染。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]

PROBE = r'''
import io, json, os, sys
tree, files = sys.argv[1], sys.argv[2].split(",")
sys.path.insert(0, tree)
import core
out = {}
for f in files:
    p = os.path.join(tree, "data", f)
    if not os.path.exists(p):
        out[f] = None
        continue
    bars = json.load(io.open(p, encoding="utf-8"))
    if isinstance(bars, dict):
        bars = bars.get("bars") or bars.get("klines") or bars
    r = core.analyze(bars)
    out[f] = {
        "centers": [{k: v for k, v in z.items() if k not in ("rel", "kind")}
                    for z in r["centers"]],
        "seg_centers": [{k: v for k, v in z.items() if k not in ("rel", "kind")}
                        for z in r["seg_centers"]],
    }
sys.stdout.write(json.dumps(out, sort_keys=True, ensure_ascii=False, default=str))
'''


def run_tree(py_path, files):
    code = os.path.join(py_path, "notes", "_probe_tmp.py")
    with io_open(code, "w") as fh:
        fh.write(PROBE)
    try:
        p = subprocess.run([sys.executable, code, py_path, ",".join(files)],
                           capture_output=True, text=True)
    finally:
        os.remove(code)
    if p.returncode:
        raise SystemExit("子进程失败（%s）：\n%s" % (py_path, p.stderr[-2000:]))
    return json.loads(p.stdout)


def io_open(path, mode):
    import io
    return io.open(path, mode, encoding="utf-8")


def strip(d):
    """剥掉两个新键（含递归里的 seg_centers）。"""
    o = {}
    for f, v in d.items():
        if v is None:
            o[f] = None
            continue
        o[f] = {}
        for layer, zs in v.items():
            o[f][layer] = [{k: x for k, x in z.items()
                            if k not in ("status", "status_note")} for z in zs]
    return o


def dist(zs, key):
    d = {}
    for z in zs:
        d[z.get(key)] = d.get(z.get(key), 0) + 1
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="HEAD")
    a = ap.parse_args()

    before_sha = subprocess.run(["git", "rev-parse", a.before], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    tmp = tempfile.mkdtemp(prefix="statusbefore-")
    try:
        p = subprocess.run("git archive %s | tar -x -C %s" % (before_sha, tmp),
                           shell=True, cwd=ROOT, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit("取不到改前的树：%s" % p.stderr[:300])
        bef = run_tree(tmp, FILES)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    aft_raw = run_tree(ROOT, FILES)
    aft = strip(aft_raw)

    print("改前 = %s（%s）｜改后 = 工作区" % (a.before, before_sha[:12]))
    print("文件                   中枢  延续  已确认  暂定 ｜ 终结方式")
    print("-" * 92)
    ok = True
    for f in FILES:
        b, a2 = bef[f], aft_raw[f]
        same = json.dumps(bef[f], sort_keys=True, ensure_ascii=False, default=str) == \
               json.dumps(aft[f], sort_keys=True, ensure_ascii=False, default=str)
        ok &= same
        cs = a2["centers"]
        st = dist(cs, "status")
        tm = dist(cs, "term")
        terms = " ｜ ".join("%s=%d" % (k, v) for k, v in sorted(tm.items()))
        print("%-20s %5d %5d %6d %5d ｜ %s  %s"
              % (f, len(cs), sum(1 for z in cs if z["live"]),
                 st.get("已确认", 0), st.get("暂定", 0), terms,
                 "" if same else "← ★ 剥键后仍不同！"))
        sc = a2["seg_centers"]
        if sc:
            sst = dist(sc, "status")
            print("%-20s %5s %5s %6d %5d ｜ （线段中枢）"
                  % ("  ↳ seg_centers", len(sc), sum(1 for z in sc if z["live"]),
                     sst.get("已确认", 0), sst.get("暂定", 0)))
    print("-" * 92)
    print("① 剥掉 status/status_note 后与改前逐位相同：%s" % ("✓ 是（纯增量）" if ok else "✗ 否"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
