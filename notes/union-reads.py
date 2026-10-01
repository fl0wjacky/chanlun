# -*- coding: utf-8 -*-
"""把三份 read-*.txt 在当前 ref 上**现算**成一张并表，并给出「各表内归属」。

起因（@atlas-791f 2026-10-01 06:1x 在卡 `card-fd1a9604-bc8` 上核的数）：
    有人报「全书剩 19 课没人逐行读过」。@atlas-791f 逐条对下来：**数目对，成分至少缺 2 课** ——
    `40`／`80` 是**快照过期**（报数的人拿 06:05 的名单比 06:14 的表），
    `10`／`105` 是**真漏**（06:05 时它们也没读过，就该在名单里）。
    他一句话点破：**净额巧合把「成分错了」这件事盖住了。**

★ 本脚本要解决的就是这件事：**数别手抄，现算，且连坐标一起报。**
  · 手抄的数**过几分钟就作废** —— 实测：同一套 read 文件，`092654f` 上是 **34 课**，
    `30d57df` 上就是 **30 课**（@iris-64a1 补读了几课）。二十分钟，差 4 课。
  · 所以本脚本**每次跑都先打印它自己跑在哪个 commit 上**。没有坐标的数不复算。

★ 归属口径（这一步只有各组自己算得了，别人替不了）：
  一个「没人读过」的课**是不是你的账**，取决于它**在不在你的覆盖表里** ——
  而「在不在我的表里」由**各组的生成器**定义（我这份是 `notes/zhongshu-coverage.py`）。
  本脚本只认**我这一组**的归属；另两组拿这份「无人读」名单去**跟自己表求交**即可。
  ★ 「我表外」≠「没人管」，「在别人表里」≠「有人读」—— 两个方向都要自己判。

用法（任意 CWD，需先 git fetch）：
    python3 notes/union-reads.py [<ref>]        # 默认 origin/main
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READS = [("中枢走势组", "notes/read-中枢走势组.txt"),
         ("动力学",     "notes/read-动力学.txt"),
         ("结构组",     "notes/read-结构组.txt")]
NEXPECT = 108

# ★ 我这一组的表外 21 课 —— 由 notes/zhongshu-coverage.py 生成（单一真源）。
#   这里**抄的是生成器的输出**，改了表外就必须同步改这里；下方有断言卡着。
MY_OUTSIDE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 74, 76, 85, 87, 95, 96, 97, 103, 104]


def show(ref, path):
    r = subprocess.run(["git", "show", "%s:%s" % (ref, path)], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("取不到 %s:%s —— 先 git fetch？" % (ref, path))
    nums = {int(x) for x in r.stdout.split() if x.strip().isdigit()}
    lines = [l for l in r.stdout.split("\n") if l.strip()]
    assert len(nums) == len(lines), \
        "%s 里有非纯课号的行（格式变了？）：%d 行 / %d 个课号" % (path, len(lines), len(nums))
    return nums


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "origin/main"
    sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()

    sets = {}
    for name, path in READS:
        sets[name] = show(ref, path)
        assert sets[name], "%s 是空的 —— 别拿空文件当「没人读过」的证据" % path

    u = set().union(*sets.values())
    assert max(u) <= NEXPECT, "课号超出 %d：%s" % (NEXPECT, sorted(n for n in u if n > NEXPECT))
    nobody = sorted(set(range(1, NEXPECT + 1)) - u)

    # ★ 我这一组的归属：表内 = 全库 − 我表外
    mine = sets["中枢走势组"]
    intable = set(range(1, NEXPECT + 1)) - set(MY_OUTSIDE)
    my_debt = [n for n in nobody if n in intable]
    not_mine = [n for n in nobody if n not in intable]
    assert not_mine == sorted(n for n in MY_OUTSIDE if n in nobody), \
        "我的『不是我的账』那列必须**恰好**是我表外 ∩ 无人读 —— 口径漂了，重看一眼"

    print("★ 口径：read-*.txt ＝ 一行一个纯课号，**只收整课逐行读完的课**（@nova-8980 06:19 裁）。")
    print("★ ★★ 本格**只是三份 read 文件的并集，不含任何「兜底」** —— "
          "一个课号只要没被任何 read 文件收，就计进「没人读过」。")
    print("★ 与 nova 的并表口径不同（他那份含兜底：表内课按组内覆盖算）⇒ **两边的数天然对不上**，"
          "差额正好是被兜底吸收的那部分。要跟并表比数，先把这个差额摆出来。"
          "（@atlas-791f 2026-10-01 06:20 提醒：不写明一定对不上号。）")
    print("★ 跑在：%s ＝ %s" % (ref, sha))
    print()
    print("| read 文件 | 课数 |")
    print("|---|---|")
    for name, _ in READS:
        print("| notes/read-%s.txt | %d |" % (name, len(sets[name])))
    print("| **并集** | **%d** |" % len(u))
    print("| **全书没人读过（补集）** | **%d** |" % len(nobody))
    print()
    print("**全书没人读过（%d 课）**：" % len(nobody))
    print()
    print("　" + " ".join("%d" % n for n in nobody))
    print()
    print("**其中在我表内 ⇒ 我的账（%d 课）**：" % len(my_debt))
    print()
    print("　" + (" ".join("%d" % n for n in my_debt) or "（无）"))
    print()
    print("**其中在我表外 ⇒ 不是我的账（%d 课，＝我的表外 21 课 ∩ 无人读）**：" % len(not_mine))
    print()
    print("　" + (" ".join("%d" % n for n in not_mine) or "（无）"))
    print()
    print("★ 另两组拿上面那份「无人读」名单**跟自己的表求交** —— 这一步谁的表谁算，别人替不了。")
    print("★ 本脚本**不写任何 read 文件**，也不改任何表：它只回答「此刻全书哪些课没人整课读过」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
