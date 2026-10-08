# -*- coding: utf-8 -*-
"""tradingview/chanlun.pine 的同步检查程序（pine lockstep）。

要回答的**唯一**问题：**自从 chanlun.pine 最后一次被改动以来，引擎的输出变了没有？**
    没变 ⇒ pine 不用动（哪怕中间过了 152 个提交）
    变了 ⇒ pine 必须重移植 —— 并指出**是哪个键、哪份数据**变了

★ 基线**不是**手写的 sha，是现取的：`git log -1 -- tradingview/chanlun.pine`。
  理由：手写基线会在"有人改了 pine 但忘了改常数"时**静默过期**，而屏幕上与一次合法通过逐字同形。

★★ 量的是**两层**，键名分得开：
    `<数据>.json`        结构层 —— `core.analyze()` 的整份输出（分型 / 笔 / 线段 / 中枢）
    `<数据>.json|seg|pen` 信号层 —— `core.signals()` 的输出（买卖点）
  原先**只量结构层**。后果实测过：第二轮把 `signals()`（背驰判据 + 前提③）改了、买卖点从 156
  变 154，这个程序照样印 `rc=0 引擎输出逐位相同 ⇒ pine 不用动` —— 而 pine 确实移植了买卖点
  （`signalsOf`），于是**引擎与 pine 在信号层已经不同步，尺子却看不见**。信号层的键补上以后，
  只动 `signals()` 的改动也会红。

★ 这个程序证的是「**陈旧**」：引擎自 pine 上次改动以来变没变。它**不证**「pine 算得对」——
  Pine 在这台机器上编译不了、跑不了，所以一次移植对不对，得靠人读（本轮另配了
  `notes/pine-p3-parity.py`：把 pine 新写的算法逐行抄成 Python 跟引擎对账）。

用法：
    python3 tools/pine_lockstep.py                # 基线 vs origin/main
    python3 tools/pine_lockstep.py --head <sha>   # 基线 vs 指定的提交
    python3 tools/pine_lockstep.py --self-test    # 两条正臂自证：结构层一对已知不同的提交 ＋
                                                  # 信号层「故意改一个信号」（压背驰比例），都必须红
退出码：
    0  输出逐位同 ⇒ pine 不用改
    1  ★ 输出不同 ⇒ pine 要改（印出差异键与数据名）
    2  跑不动（取不到树 / 数据缺 / 引擎抛异常）—— **查不了 ≠ 通过**
    3  --self-test 的**正臂没红** ⇒ 这个检查程序本身不算数；或者两边共同的键是 0 / 少于只有一边有的 ⇒ 没比成
"""
import argparse, hashlib, io, importlib, json, os, re, shutil, subprocess, sys, tempfile

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


SIGNAL_LEVELS = ("seg", "pen")        # 与 pine 的 sigLevel 两个选项对应（线段中枢 / 类中枢）
# ★ 信号层只哈希 **Pine 移植了的那几个字段**（Nova 10-08 17:10）：跟 chanlun.pine 的 `type Sig` 一一对应（kind/bar/price/confirmed/weak）。
#   引擎的 signals() 还带 why、level、center、unit、std 这类 Pine 根本不输出的字段 —— 改它们 Pine 不用动，尺子不该红
#   （M29 把二卖的 why 从「不创新低」改成「不创新高」，整片信号键红了，Pine 一行不用改）。
#   名单不许悄悄变宽：--self-test 会拿它跟检出树里 `type Sig` 的字段逐个对，多一个、少一个都报（exit=3）。
#   这不是「忽略标注字段」的开关：名单是正面列出来的「Pine 有什么」，引擎新加任何字段默认都不参与，
#   要参与就得 Pine 先有 —— 跟 signalsOf 对齐，而不是跟引擎对齐。
PINE_SIG_FIELDS = ("kind", "bar", "price", "confirmed", "weak")


def outputs(tree, perturb=False):
    """{键: sha256(输出)} —— 结构层 `<数据>.json` ＋ 信号层 `<数据>.json|seg|pen`。

    整支在一个子进程里跑，避免两棵树的 core 互相污染。

    perturb=True 时把背驰比例压到 0（**只动信号层，不动结构层**）—— 给 --self-test 的信号层
    正臂用：同一棵树上改了信号，信号键**必须**变，否则说明这个探针根本没接上。
    perturb="why" 时只把每颗点的 why 改掉（Pine 没有的字段）—— 信号键**必须不变**。
    """
    code = r'''
import hashlib, io, json, os, sys
tree, outp, mode, fields = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
perturb = mode == "1"
sys.path.insert(0, tree)
import core

def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()[:16]
out = {}
for f in sorted(os.listdir(os.path.join(tree, "data"))):
    if not f.endswith(".json"): continue
    try:
        bars = json.load(io.open(os.path.join(tree, "data", f), encoding="utf-8"))
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines") or bars
    except Exception as e:
        out[f] = "读不动:%s" % type(e).__name__
        continue
    try:
        r = core.analyze(bars)
    except Exception as e:
        out[f] = "analyze 跑不动:%s" % type(e).__name__
        continue
    out[f] = H(r)
    for lv in ("seg", "pen"):                      # 信号层：买卖点
        k = "%s|%s" % (f, lv)
        try:
            sg = core.signals(r, lv, "macd", ratio=(0.0 if perturb else 1.0))
            if mode == "why":
                sg = [dict(x, why="拧坏的说明文字") for x in sg]
            out[k] = H([{f: x.get(f) for f in fields} for x in sg])   # 只哈希 Pine 移植了的字段（PINE_SIG_FIELDS）
        except Exception as e:
            out[k] = "signals 跑不动:%s" % type(e).__name__
json.dump(out, open(outp, "w"))
'''
    fd, tmp = tempfile.mkstemp(suffix=".json"); os.close(fd)
    mode = perturb if perturb == "why" else ("1" if perturb else "0")
    p = subprocess.run([sys.executable, "-c", code, tree, tmp, mode, ",".join(PINE_SIG_FIELDS)],
                       capture_output=True, text=True)
    if p.returncode:
        print("★ 引擎在 %s 上跑不动 ⇒ 查不了（**不是「通过」**）：" % tree)
        print(p.stderr.strip()[-800:])
        raise SystemExit(2)
    return json.load(io.open(tmp, encoding="utf-8"))


def ref_tree(sha, perturb=False):
    d = materialize(sha)
    try:
        return outputs(d, perturb)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def split_keys(keys):
    """把键分成结构层 / 信号层两拨（信号键形如 `zec_1h.json|pen`）。"""
    struct = sorted(k for k in keys if "|" not in k)
    sigs = sorted(k for k in keys if "|" in k)
    return struct, sigs


def compare(a_sha, b_sha, label_a, label_b):
    print("基线 %s = %s   %s" % (label_a, a_sha[:12], PINE))
    print("对照 %s = %s" % (label_b, b_sha[:12]))
    A = ref_tree(a_sha)
    B = ref_tree(b_sha)
    # 只比**两边都有**的数据：基线之后新加的样本（如 data/zec30_cut.json）在基线里本来就没有，
    # 「None → hash」不是引擎变了，是多了一份数据。原先它也算红 ⇒ 每加一份夹具 pine 就"必须重移植"，假红。
    # 删掉的样本同理。两边都有的数据照旧逐键比，引擎一变照样红（--self-test 两条正臂不受影响）。
    only = sorted((set(A) ^ set(B)))
    keys = set(A) & set(B)
    bad = [(k, A.get(k), B.get(k)) for k in sorted(keys) if A.get(k) != B.get(k)]
    if only:
        print("  （只有一边有、不比的键 %d 个：%s）" % (len(only), "、".join(only[:6]) + ("…" if len(only) > 6 else "")))
    if not keys or len(only) > len(keys):
        # 空转防线（Atlas 核 d4fd3c3 时提）：共同键是 0，或只有一边有的比共同的还多（样本整批改名、ref 对错）
        # ⇒ 根本没比成，不许印「逐位相同」
        print("  ★ 没比成：共同的键 %d 个、只有一边有的 %d 个 ⇒ 查不了（**不是「不用动」**）。" % (len(keys), len(only)))
        return 3
    struct, sigs = split_keys(keys)
    bad_s = [k for k, _x, _y in bad if "|" not in k]
    bad_g = [k for k, _x, _y in bad if "|" in k]
    print("  结构层 %d 个键（%d 不同）· 信号层 %d 个键（%d 不同）"
          % (len(struct), len(bad_s), len(sigs), len(bad_g)))
    if not bad:
        print("  ⇒ 引擎输出**逐位相同**（结构 + 信号）⇒ `%s` 不用动。" % PINE)
        return 0
    print("  ⇒ ★ 引擎输出变了 ⇒ `%s` **必须重移植**：" % PINE)
    for k, x, y in bad:
        print("      %-28s %s → %s" % (k + ("  [信号层]" if "|" in k else "  [结构层]"), x, y))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default=None, help="对照的提交（默认 origin/main）")
    ap.add_argument("--self-test", action="store_true",
                    help="两条正臂：结构层一对已知不同的提交，信号层「故意改一个信号」，都必须红")
    a = ap.parse_args()

    if a.self_test:
        # ── 正臂①（结构层）：一对已知引擎被重写过的提交，输出必须不同
        rc = compare(SELFTEST_OLD, SELFTEST_NEW, "自证·旧", "自证·新")
        if rc == 0:
            print("★ 正臂①（结构层）**没红** ⇒ 这个检查程序判不出差异 ⇒ 它印的「不用动」不算数（exit=3）。")
            return 3
        print("⇒ 正臂①（结构层）红了（exit=%d）✓" % rc)

        # ── 正臂②（信号层）：同一棵树，把背驰比例压到 0 —— **故意改一个信号**，信号键必须变。
        #    没有这一条，"只动 signals() 的改动"照样能印出绿色的「不用动」（2026-10-02 实测踩过）。
        tree = a.head or "HEAD"
        A = ref_tree(tree, perturb=False)
        B = ref_tree(tree, perturb=True)
        sig_keys = [k for k in A if "|" in k]
        if not sig_keys:
            print("★ 正臂②（信号层）**一个信号键都没有** ⇒ 探针没接上（exit=3）。")
            return 3
        moved = [k for k in sig_keys if A[k] != B.get(k)]
        if not moved:
            print("★ 正臂②（信号层）**没红**：改了背驰比例，%d 个信号键一个没变 ⇒ 这个探针不算数（exit=3）。"
                  % len(sig_keys))
            return 3
        print("⇒ 正臂②（信号层）红了：把背驰比例压到 0 ⇒ %d/%d 个信号键变了 ✓"
              % (len(moved), len(sig_keys)))
        print("    （探针连上了。它**不**证明引擎算得对，只证明「信号一变，它就看得见」。）")

        # ── 臂③：只改 why（Pine 没有的字段）⇒ 信号键必须**一个都不变**
        C = ref_tree(tree, perturb="why")
        drift = [k for k in sig_keys if A[k] != C.get(k)]
        if drift:
            print("★ 臂③ 只改 why 却有 %d 个信号键变了（例 %s）⇒ 名单外的字段混进了哈希（exit=3）。" % (len(drift), drift[:2]))
            return 3
        print("⇒ 臂③ 只改 why（Pine 不输出的字段）⇒ %d 个信号键一个没变 ✓" % len(sig_keys))

        # ── 臂④：名单跟检出树里 chanlun.pine 的 `type Sig` 逐个对，多一个、少一个都报
        d = materialize(tree)
        try:
            src = io.open(os.path.join(d, PINE), encoding="utf-8").read()
        finally:
            shutil.rmtree(d, ignore_errors=True)
        m = re.search(r"^type Sig\n((?:[ \t]+\S+[ \t]+\w+.*\n)+)", src, re.M)
        pine = [re.split(r"\s+", ln.strip())[1] for ln in m.group(1).splitlines()] if m else []
        extra = [f for f in PINE_SIG_FIELDS if f not in pine]
        missing = [f for f in pine if f not in PINE_SIG_FIELDS]
        if not pine or extra or missing:
            print("★ 臂④ PINE_SIG_FIELDS 跟 %s 的 type Sig 对不上：名单多了 %s、少了 %s（Pine 里是 %s）（exit=3）。"
                  % (PINE, extra, missing, pine))
            return 3
        print("⇒ 臂④ PINE_SIG_FIELDS 跟 type Sig 逐个对上：%s ✓" % ", ".join(pine))
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
