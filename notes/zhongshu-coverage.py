# -*- coding: utf-8 -*-
"""中枢走势组：覆盖表 ＋ 逐行已读名单，**同一次产出**。

为什么合成一个脚本（nova 2026-10-01 05:21 定的口径）：
  「并表只看这三份（`notes/read-*.txt`），不再从正文里去捞……最好用你们的生成脚本
    现算写出来，跟覆盖表同一个来源，别手抄，免得再出 §0 和 §7 对不上那种事。」
  ⇒ 名单**不是**手敲的一串数字，是从**本组成品（inventory_中枢走势组.md）的十一个附录**
    里反解出来的；覆盖表是同一次运行从语料现算的。**两个数出自同一次跑**，不可能漂开。

用法（在 wt-concepts worktree 根跑）：
    python3 notes/zhongshu-coverage.py            # 只打印
    python3 notes/zhongshu-coverage.py --write-read   # 打印并把名单写回

★ 行数口径：`len(read().replace("\\r","").split("\\n"))` —— 比 `wc -l` **每课多 1**
  （语料每课末尾没有换行符）。报数时必须说清是哪把尺。
"""
import glob
import os
import re
import sys

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(WT, "docs/concepts/inventory_中枢走势组.md")
OUT = os.path.join(WT, "notes/read-中枢走势组.txt")

# 词场两档。★ 这里是**唯一**一份定义，卡上那张表是从这里现算的，别在别处再抄一遍。
SPECIFIC = ["中枢震荡", "走势终完美", "必完美", "同级别分解", "非同级别分解",
            "中枢扩展", "扩张", "延伸", "新生", "走势中枢", "分解定理", "中枢定理",
            "结合律", "中阴", "多义性", "震荡中轴", "平衡市", "递归",
            "ZG", "ZD", "自同构"]
COMMON = ["中枢", "走势类型", "级别", "分解"]


def load():
    out = {}
    for p in sorted(glob.glob(os.path.join(WT, "archive/chanlun108/text/lesson-*.txt"))):
        n = int(re.search(r"(\d+)", os.path.basename(p)).group(1))
        out[n] = open(p, encoding="utf-8").read().replace("\r", "")
    return out


def read_set():
    """从本组成品的附录里反解「整课逐行读完」的课号。

    两种写法都认（附录三/四是分批报的，附录五起是 `**批 N**：` 行）：
      · 附录三/四：`\\`L44\\`(88)` 这种「课号(行数)」对
      · 附录五起：`**批 N**：\\`L31\\`(299) · \\`L28\\`(262) · …`
    ★ 只认**正文里明确写了「逐行读完」的那几节**，不是全篇见到的 `Lxx` ——
      正文里引文行号到处都是，全捞会把「提到过」当成「读过」。
    """
    doc = open(DOC, encoding="utf-8").read()
    got = {}
    # ★ 「十一」的「一」必须在这个字符类里 —— 少了它，附录十一会被**静默跳过**
    #   （第一次跑就踩了：已精读报 33 而不是 36，正好差最后一批）。
    for m in re.finditer(r"^## 附录[一二三四五六七八九十]+：.*?$\n(?:(?!^## ).)*", doc, re.M | re.S):
        body = m.group(0)
        head = body.split("\n", 1)[0]
        if "通读增量" not in head:
            continue
        m2 = re.search(r"\*\*批 \d+\*\*：(.+)", body)
        if m2:                       # 附录五起的格式
            seg = m2.group(1)
        else:                        # 附录三/四：整节里所有「课号(行数)」对
            seg = body
        for n, ln in re.findall(r"`L(\d+)`\((\d+)\)", seg):
            got[int(n)] = int(ln)
    return got


def main():
    L = load()
    spec = {n: sum(v.count(t) for t in SPECIFIC) for n, v in L.items()}
    comm = {n: sum(v.count(t) for t in COMMON) for n, v in L.items()}
    nlines = {n: len(v.split("\n")) for n, v in L.items()}

    read = read_set()
    # ★ 自检：附录里写的课长必须与语料现算逐字相同，否则宁可炸掉也不写文件
    for n, ln in read.items():
        assert nlines[n] == ln, "L%d 课长对不上：附录写 %d，现算 %d" % (n, ln, nlines[n])
    assert len(set(read)) == len(read), "名单里有重复课号"

    in_table = [n for n in L if spec[n] >= 1 or comm[n] >= 4]      # 覆盖表的行
    out_table = [n for n in L if n not in in_table]                # 表外
    owed4 = [n for n in L if spec[n] >= 4]                         # 挂在①上的门槛
    unread = [n for n in in_table if n not in read]

    print("★ 口径：次数＝删换行后 count；行数＝read().split(\"\\n\")（比 wc -l 每课多 1）")
    print()
    print("| 档 | 课数 | 合计行数 |")
    print("|---|---|---|")
    for name, ns in (("特异词 ≥4（**门槛挂这里**）", owed4),
                     ("特异词 ≥1 或通场词 ≥4（覆盖表行）", in_table),
                     ("表外（覆盖表没有的课）", out_table),
                     ("**已精读（逐行读完）**", sorted(read)),
                     ("**★未读**（表内 − 已读）", unread)):
        print("| %s | %d | %d |" % (name, len(ns), sum(nlines[n] for n in ns)))
    print()
    print("匀账：全库 %d 课 %d 行 ＝ 表内 %d 课 %d 行 ＋ 表外 %d 课 %d 行"
          % (len(L), sum(nlines.values()), len(in_table), sum(nlines[n] for n in in_table),
             len(out_table), sum(nlines[n] for n in out_table)))
    print("名单：%s（%d 课）" % (os.path.relpath(OUT, WT), len(read)))

    if "--write-read" in sys.argv:
        body = "".join("%d\n" % n for n in sorted(read))
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        open(OUT, "w", encoding="utf-8").write(body)
        print("→ 已写回（%s）" % ("内容有变" if old != body else "内容未变"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
