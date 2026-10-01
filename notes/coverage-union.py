#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三组「覆盖表内」集合求并 —— 现算，并印出它跑在哪个 commit 上。

为什么有这个脚本（bram 2026-10-01 在 card-fd1a9604-bc8 上定的规矩）：
  「它们到底归谁，要三张表**现算**的表内集合求并，不能拿名单顶。」
  「并表必须脚本现算、并印出它跑在哪个 commit 上。」
→ 跟 checkquotes.py 印语料指纹是同一个道理：**不带坐标的数，过一小时就没人能复算。**

三个来源（口径**不相同**，别当成同一把尺）：

  1 结构组  docs/concepts/inventory_结构组.md    §7 表：8 列（课|…|合计|…|状态）
           门槛 = 本组词场「信号 ≥4」
  2 动力学  docs/concepts/inventory_动力学.md    §15 覆盖表：末列为状态
           门槛 = 本文件里写死的那条（见其 §15 抬头）
  3 中枢组  ★ **本组的覆盖表不在仓库里，在卡 card-fd1a9604-bc8 上。**
           故此处只能用 bram 在卡上贴的『表外 21 课』取补，**不是全仓可复算**。
           门槛 = 「特异词 ≥1 或 通场词 ≥4」

★ 本脚本【只读】：不写任何文件。用到的 git 命令只有 show / rev-parse / ls-tree。
★ 它算的是「表内」与「有无 read 文件」，**不是「读没读过」** —— read 文件只是
  *机器可查的* 读完记录；某组读过而没落 read 文件，本脚本看不见。报数时必须带这句。

用法： python3 notes/coverage-union.py [ref]   # ref 默认 origin/main
"""
import re
import subprocess
import sys

REPO = "."


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True)


def show(path, ref):
    """★ 取不到就当场炸。git show 失败只是空 stdout —— 静默返回空串
    会让下游把「文件不在这个 ref 上」读成「这张表 0 课」（我第一版就是这么错的）。"""
    r = git("show", "%s:%s" % (ref, path))
    if r.returncode != 0:
        raise SystemExit("取不到 %s:%s\n  %s" % (ref, path, r.stderr.strip()))
    return r.stdout


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_courses(txt, ncol, status_col_last=False, statuses=None):
    """取 markdown 表里的课号。行必须是 ncol 列、首列是纯数字。"""
    got = set()
    for ln in txt.split("\n"):
        if not ln.startswith("|"):
            continue
        c = _cells(ln)
        if len(c) != ncol or not re.fullmatch(r"\d{1,3}", c[0]):
            continue
        if status_col_last and statuses is not None and c[-1] not in statuses:
            continue
        got.add(int(c[0]))
    return got


STATUS_WORDS = {"★未读", "已精读", "逐行", "已读", "未读", "抽读"}

# 中枢组：bram 在卡 card-fd1a9604-bc8 上贴的「表外 21 课」（他声明为现算）。
# ★ 这一串不在仓库里 —— 它变了必须手改这里，改的时候连卡的 seq 一起写。
ZS_OUTSIDE_FROM_CARD = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 74, 76,
                        85, 87, 95, 96, 97, 103, 104]

ALL = set(range(1, 109))


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    rp = git("rev-parse", "--verify", "%s^{commit}" % ref)
    if rp.returncode != 0:
        raise SystemExit("这个 ref 不存在：%s" % ref)
    print("现算坐标：%s = %s" % (ref, rp.stdout.strip()[:7]))
    print()

    A = table_courses(show("docs/concepts/inventory_结构组.md", ref), 8)
    # 动力学表的列数不固定（同文件里还有别的表）⇒ 不走 ncol 分支，按末列状态词扫
    I = set()
    for ln in show("docs/concepts/inventory_动力学.md", ref).split("\n"):
        c = _cells(ln) if ln.startswith("|") else []
        if len(c) >= 3 and re.fullmatch(r"\d{1,3}", c[0]) and c[-1] in STATUS_WORDS:
            I.add(int(c[0]))
    B = ALL - set(ZS_OUTSIDE_FROM_CARD)

    print("① 结构组 表内 = %3d 课   （文档 §7 现取 · 门槛：信号 ≥4）" % len(A))
    print("② 动力学 表内 = %3d 课   （文档 §15 现取 · 末列状态过滤）" % len(I))
    print("③ 中枢组 表内 = %3d 课   ★ 非仓库现算：108 − 卡上贴的表外 %d 课"
          % (len(B), len(ZS_OUTSIDE_FROM_CARD)))
    U = A | I | B
    print("   ────────────────────────────────────────────")
    print("   三张表内并集 = %3d 课" % len(U))
    print()

    rf, per = set(), []
    names = [f for f in git("-c", "core.quotepath=false", "ls-tree", "-r",
                            "--name-only", ref).stdout.split("\n")
             if re.search(r"read-.*\.txt$", f)]
    for n in sorted(names):
        got = set(int(m) for m in re.findall(r"(?m)^\s*(\d{1,3})\s*$", show(n, ref)))
        per.append((n.split("/")[-1], len(got)))
        rf |= got
    print("   read 文件（机器可查的读完记录）：")
    for nm, k in per:
        print("     %-22s %3d 课" % (nm, k))
    print("     %-22s %3d 课" % ("并集", len(rf)))
    print()

    def fmt(s):
        return " ".join(str(x) for x in sorted(s))

    never = ALL - U
    in_tbl_no_read = U - rf
    print("★ 三张表【都没收】的课 = %2d 课" % len(never))
    print("   " + fmt(never))
    print("   ★ 其中「不在中枢组表内」是取补算出来的（构造使然，不算独立验证）；")
    print("     「不在结构组 35 课、也不在动力学 88 课里」是两份文档现算 —— 这一半是独立的。")
    print()
    print("★ 在某张表内、但【没有 read 文件】= %2d 课" % len(in_tbl_no_read))
    print("   " + fmt(in_tbl_no_read))
    print("   ★ 这不等于「欠 19 课」：read 文件只是机器可查的记录，")
    print("     某组读过而没落 read 文件的情形本脚本看不见。")
    print()
    print("（核对：108 − %d = %d；读文件并集 %d ⊆ 表内并集 %d ⇒ %s）"
          % (len(U), len(never), len(rf), len(U), len(rf) <= len(U)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
