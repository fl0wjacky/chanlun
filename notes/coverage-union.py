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
  3 中枢组  ★★ **本组的覆盖表不在仓库里，在卡 card-fd1a9604-bc8 上。**
           故此处只能用 bram 在卡上贴的『表外』名单取补，**不是全仓可复算**。
           ⇒ 输出里印来源＋时刻＋条数。**别把它当稳定输入，也别去和 23／20 相减**
           —— 那三个数不是同一格的三次读数，是三套口径（见 ZS_STALE_NOTE 上方那通碑）。
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

# ── 中枢组：★ 本脚本唯一的「仓外 + 手抄」输入，也是唯一会漂的一格 ──────────────
#   bram 的覆盖表不在仓库里（在卡 card-fd1a9604-bc8 上），只能拿他的「表外」取补。
#   ★★ 实测这串当天就在漂：卡上 06:14 报 21 课 → 群 06:2x 报 20 课 → 他文档仍写 23 课。
#   ⇒ 所以这里**不静默用**：把来源、时刻、条数都印出来，条数对不上就当场炸。
ZS_OUTSIDE_FROM_CARD = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 74, 76,
                        85, 87, 95, 96, 97, 103, 104]
ZS_ASOF = "卡 card-fd1a9604-bc8 · bram 2026-10-01T06:14Z（列表逐字来自他卡上那条）"
# ★★★ 这一行是给未来的我立的碑。我一度写下「表外今天走了 23 → 21 → 20」，
#   还据此逐项算出「两版之差恰好是第 103 课进表」——**算术全对，前提全错**：
#   那三个数是**三套口径**，我拿它们互相减。
#   bram 2026-10-01 更正：表外＝21 课 1090 行（`notes/zhongshu-coverage.py` 现算，本条常量对）；
#   23 是附录九末条那笔**旧账**（门槛严一档）；**20 根本不是表外**，是「表外 ∩ 全书没人读过」，
#   是**另一个量**。⇒ 我拿来相减的两个集合，量纲都不一样。
#   ★ 同一条病我当天骂过别人（「名单是快照、表内是现算，不能对着数」），转头自己犯。
#   ⇒ 以后凡是「同一格出现了两个数」，先问是不是同一个量，再谈差。
ZS_STALE_NOTE = ("★ 三个数常被并成一个：表外 **21 课 1090 行**（现算，＝本常量）· 附录九旧账 **23**"
                 "（门槛严一档）· **20** 是「表外 ∩ 全书没人读过」，另一个量。**不许相减。**"
                 "⇒ bram 说批 11 后加 `--dump-table` 把表内／表外课号写进仓库，届时本格改为直读。")
_ZS_EXPECT = 21

# ★ 说清楚这把锁能锁什么、锁不了什么：
#   - 它锁得住「有人改了名单却没改时刻/条数」（改动检测）；
#   - 它**锁不住「卡上的数变了而没人动这行」** —— 脚本看不见卡。那种漂只有人能发现，
#     所以唯一的防线是**把来源和时刻印在输出里**，让读的人自己看日期。
assert len(ZS_OUTSIDE_FROM_CARD) == _ZS_EXPECT, \
    "中枢组表外常量被改成 %d 课（原 %d）：请连 ZS_ASOF／ZS_STALE_NOTE／_ZS_EXPECT 一起更新" \
    % (len(ZS_OUTSIDE_FROM_CARD), _ZS_EXPECT)
assert len(set(ZS_OUTSIDE_FROM_CARD)) == len(ZS_OUTSIDE_FROM_CARD), "中枢组表外名单里有重复课号"

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
    print("③ 中枢组 表内 = %3d 课   ★★ 非仓库现算：108 − 卡上贴的表外 %d 课"
          % (len(B), len(ZS_OUTSIDE_FROM_CARD)))
    print("      来源：%s" % ZS_ASOF)
    print("      %s" % ZS_STALE_NOTE)
    print("      ★ ②③ 两格的口径不同（门槛不同），**并集不代表任何一张表**；")
    print("        报 ③ 必须连上面的来源一起报 —— 它**不是仓库现算**。")
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
    print("（核对：108 − %d = %d；读文件并集 %d · 表内并集 %d）"
          % (len(U), len(never), len(rf), len(U)))
    # ★ 这里原本只印一句 `读文件 ⊆ 表内 ⇒ False` —— **那句话把一件正常事写成了故障**。
    #   差集就是上面那批散课：某组（这里是兜底组）读了、而三张表**都没收**的课，
    #   正是 108 − 表内并集 那一格。⇒ 把它**点名印出来**，别让读的人自己猜 False 是什么意思。
    # ★ 「同集」也现算 —— 恒有 rf−U ⊆ never；两集相等只是**这一次**的事实，不能写死。
    print("★ 读了、但【不在任何一张表内】= %2d 课（%s『都没收』那集）"
          % (len(rf - U), "同" if rf - U == never else "★ 不等于"))
    print("   " + fmt(rf - U))
    print("   ★ 这不是错位：**读的账可以超出表的账** —— 兜底组的存在理由就是这个。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
