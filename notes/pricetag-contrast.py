# -*- coding: utf-8 -*-
"""价签（中枢 `[ZD, ZG]` / `↑高N级`）的**底色、字色、对比度**：从两张成图上量，不从公式推（只读）。

为什么要有这个：2026-10-02 价签统一成「30% 同色底 ＋ 白字」（A 表那一行，小栋拍）之后，
报告里出现两个数 —— **改后 9.1:1 ／ 改前 11.2:1**，新的比旧的**低**。这两个数必须能被复跑，
不然「新的低一点但没关系」就只是我一句话。这个脚本是那把尺。

★ 为什么「改前」那个 11.2:1 不能当成「改前更好读」：
  改前 `draw_labels` 的底是 `BG + 215`（深底压深面板）⇒ 在这张图上**根本量不到底**，
  同窗口里最多的两种颜色就是面板色 `(16,18,24)` 和字色本身。
  那个 11.2 是「字 对 面板」算的 —— **字和 K 线之间没有任何东西隔开**。
  改后才有底。所以这一改买到的是「有底」，不是「更亮」。脚本把这一点印出来，不靠人记。

★★ 复跑需要**两棵树**（改前 = `agent/iris/price-tag` 的基线 `11a6d43`）：

    git worktree add --detach /tmp/cl-before 11a6d43
    cd /tmp/cl-before && python3 render/chart_zec_segments.py && cp out/zec15_duan.png /tmp/before.png
    cd <本仓> && python3 render/chart_zec_segments.py && cp out/zec15_duan.png /tmp/after.png
    python3 notes/pricetag-contrast.py /tmp/before.png /tmp/after.png

窗口 `BOX` 是**线段中枢价签**（zec15 线段概览图上的第一个）所在的矩形 ——
换数据 / 换图就得重新定位：找「30% 琥珀压在底色上」的那个混合色 `(84, 71, 40)` 的连通块。

    python3 notes/pricetag-contrast.py <改前.png> <改后.png>
退出码：0 = 量到了两种颜色且对比度都在 WCAG AA(4.5) 之上；1 = 没量到（窗口错了 / 图变了）。
"""
import collections
import sys

from PIL import Image

BOX = (500, 592, 712, 628)          # zec15 线段概览图：第一个线段中枢价签
BG = (16, 18, 24)                   # render/style.py 的页面底色
PANEL_OLD = BG                      # 改前那个「底」= BG+215 压在面板上 ⇒ 量出来就是面板色


def lum(c):
    s = [v / 255 for v in c]
    lin = [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in s]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def read(path, box=BOX):
    """→ (底色, 字色)。底色 = 窗口内出现最多的颜色；字色 = 最亮那一撮的中位数。"""
    px = list(Image.open(path).convert("RGB").crop(box).getdata())
    cnt = collections.Counter(px)
    bg = cnt.most_common(1)[0][0]
    top = max(sum(p) for p in px)
    bright = [p for p in px if sum(p) > top - 60]
    n = len(bright)
    txt = tuple(sorted(c[i] for c in bright)[n // 2] for i in range(3))
    return bg, txt, cnt


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    before, after = argv[1], argv[2]
    bad = 0
    for name, path, old in (("改前", before, True), ("改后", after, False)):
        bg, txt, cnt = read(path)
        r = contrast(bg, txt)
        print("%s  底 = %-16s 字 = %-16s 对比度 %.1f:1" % (name, bg, txt, r))
        if max(cnt.values()) < 100:
            print("   ★ 窗口里没有一块成片的底色（最多才 %d px）—— 窗口定位错了，读数不算数"
                  % max(cnt.values()))
            bad += 1
        if r < 4.5:
            print("   ★ 低于 WCAG AA(4.5:1)")
            bad += 1
    # 改前那一格的底色**应当**等于面板色 —— 那正是「底看不见」的证据；不是就说明窗口错了
    if read(before)[0] != PANEL_OLD:
        print("★ 改前窗口里最多的颜色不是面板色 %s ⇒ 窗口可能压到了别的东西，两格的对照不成立" % (PANEL_OLD,))
        bad += 1
    if read(after)[0] == read(before)[0]:
        print("★ 改前改后的底色量出来一样 ⇒ 要么没生效，要么窗口是空的")
        bad += 1
    else:
        print("⇒ 改前「底」= 面板色本身（看不见底）；改后才有底。差异成立。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
