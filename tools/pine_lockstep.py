# -*- coding: utf-8 -*-
"""tradingview/chanlun.pine 的同步检查程序（pine lockstep）。

要回答的**唯一**问题：**自从 chanlun.pine 最后一次被改动以来，引擎的输出变了没有？**
    没变 ⇒ pine 不用动（哪怕中间过了 152 个提交）
    变了 ⇒ pine 必须重移植 —— 并指出**是哪个键、哪份数据**变了

★ 基线**不是**手写的 sha，是现取的：`git log -1 -- tradingview/chanlun.pine`。
  理由：手写基线会在"有人改了 pine 但忘了改常数"时**静默过期**，而屏幕上与一次合法通过逐字同形。

用法：
    python3 tools/pine_lockstep.py                # 基线 vs origin/main
    python3 tools/pine_lockstep.py --head <sha>   # 基线 vs 指定的提交
    python3 tools/pine_lockstep.py --self-test    # 正臂：拿一对**已知不同**的提交自证它会红
退出码：
    0  输出逐位同 ⇒ pine 不用改
    1  ★ 输出不同 ⇒ pine 要改（印出差异键与数据名）
    2  跑不动（取不到树 / 数据缺 / 引擎抛异常）—— **查不了 ≠ 通过**
    3  --self-test 的**正臂没红** ⇒ 这个检查程序本身不算数
"""
import argparse, hashlib, io, importlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
PINE = "tradingview/chanlun.pine"

# ★ 自证用的那一对：`430e074`（v1）→ `67d1bd1`（v2.3）之间引擎被重写过（笔极值、特征序列包含、
#   三买卖终结、扩展合并），输出**必须**不同。这条是 positive 臂的锚 —— 没有它，
#   "输出没变"有两个解释：① 真的没变 ② 这个检查程序根本没接上。
SELFTEST_OLD, SELFTEST_NEW = "430e074", "67d1bd1"


def sh(cmd):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def materialize(sha):
    d = tempfile.mkdtemp(prefix="pinelock-")
    rc, _o, e = sh("git archive %s | tar -x -C %s" % (sha, d))
    if rc:
        shutil.rmtree(d, ignore_errors=True)
        raise SystemExit("取不到那棵树：%s（%s）" % (sha, e[:200]))
    return d


def outputs(tree):
    """{数据文件: sha256(analyze 输出)}。整支在一个子进程里跑，避免两棵树的 core 互相污染。"""
    code = r'''
import hashlib, importlib, io, json, os, sys
tree = sys.argv[1]; sys.path.insert(0, tree)
import core
out = {}
for f in sorted(os.listdir(os.path.join(tree, "data"))):
    if not f.endswith(".json"): continue
    try:
        bars = json.load(io.open(os.path.join(tree, "data", f), encoding="utf-8"))
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines") or bars
        r = core.analyze(bars)
        out[f] = hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False,
                                          default=str).encode()).hexdigest()[:16]
    except Exception as e:
        out[f] = "跑不动:%s" % type(e).__name__
json.dump(out, open(sys.argv[2], "w"))
'''
    fd, tmp = tempfile.mkstemp(suffix=".json"); os.close(fd)
    p = subprocess.run([sys.executable, "-c", code, tree, tmp], capture_output=True, text=True)
    if p.returncode:
        print("★ 引擎在 %s 上跑不动 ⇒ 查不了（**不是「通过」**）：" % tree)
        print(p.stderr.strip()[-800:])
        raise SystemExit(2)
    return json.load(io.open(tmp, encoding="utf-8"))


def ref_tree(sha):
    d = materialize(sha)
    try:
        return outputs(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def compare(a_sha, b_sha, label_a, label_b):
    print("基线 %s = %s   %s" % (label_a, a_sha[:12], PINE))
    print("对照 %s = %s" % (label_b, b_sha[:12]))
    A = ref_tree(a_sha)
    B = ref_tree(b_sha)
    bad = [(k, A.get(k), B.get(k)) for k in sorted(set(A) | set(B)) if A.get(k) != B.get(k)]
    n = len(set(A) | set(B))
    print("  %d 份数据 · %d 份不同" % (n, len(bad)))
    if not bad:
        print("  ⇒ 引擎输出**逐位相同** ⇒ `%s` 不用动。" % PINE)
        return 0
    print("  ⇒ ★ 引擎输出变了 ⇒ `%s` **必须重移植**：" % PINE)
    for k, x, y in bad:
        print("      %-24s %s → %s" % (k, x, y))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default=None, help="对照的提交（默认 origin/main）")
    ap.add_argument("--self-test", action="store_true", help="正臂：一对已知不同的提交，必须红")
    a = ap.parse_args()

    if a.self_test:
        rc = compare(SELFTEST_OLD, SELFTEST_NEW, "自证·旧", "自证·新")
        if rc == 0:
            print("★ 正臂**没红** ⇒ 这个检查程序判不出差异 ⇒ 它印的「不用动」不算数（exit=3）。")
            return 3
        print("⇒ 正臂红了（exit=%d）✓ —— 它接上了，所以它印的「不用动」才算数。" % rc)
        return 0

    rc, base, _e = sh("git log -1 --format=%%H -- %s" % PINE)
    if rc or not base:
        print("取不到 %s 的历史 ⇒ 查不了（exit=2）" % PINE)
        return 2
    head = a.head or "origin/main"
    rc, hsha, _e = sh("git rev-parse %s" % head)
    if rc or not hsha:
        print("取不到 %s ⇒ 查不了（exit=2）" % head)
        return 2
    if base == hsha:
        print("%s 这一提交本身就是 pine 最后一次改动 ⇒ 输出当然同（不是检查，是同义反复）。" % PINE)
        return 0
    return compare(base, hsha, "pine 最后一次改动", head)


if __name__ == "__main__":
    sys.exit(main())
