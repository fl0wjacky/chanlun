#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在本地保存的《教你炒股票》108 课全文里检索。

用法：
    python3 tools/find_original.py 中枢延伸           # 检索关键词，带上下文
    python3 tools/find_original.py 走势终完美 -n 3     # 只看前 3 处
    python3 tools/find_original.py --lesson 20        # 读第 20 课全文
    python3 tools/find_original.py --toc              # 列目录
    python3 tools/find_original.py --grep 后 ZG       # 只在含该串的段落里找（多关键词）

这样以后要用原文，先查本地；本地没有再联网。

⚠️ 本地全文有抓取噪声：约 30 课里有字被重复（「如果果」「顶顶分型」，全书 2000+ 处）。
   所以匹配时关键词与原文两边都先把「连续重复的字」压成一个再比，显示仍是原文。
   仍有少量插字型乱码（「一半根半之上」），整句搜不到时改用 2–4 字短词组合。
"""
import os, re, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "archive", "chanlun108")
FULL = os.path.join(BASE, "全文.txt")


def _norm(s):
    """把连续重复的字压成一个（两边都压，所以「谢谢」这类正常叠字也照样能匹配）。"""
    return re.sub(r"(.)\1+", r"\1", s)


def load():
    if not os.path.exists(FULL):
        sys.exit("本地还没有全文，先跑：python3 tools/fetch_chanlun108.py")
    t = open(FULL, encoding="utf-8").read()
    parts = re.split(r"\n={70}\n【第 (\d+) 课】([^\n]*)\n", t)
    out = []
    for i in range(1, len(parts), 3):
        out.append((int(parts[i]), parts[i + 1].strip(), parts[i + 2]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kw", nargs="*", help="关键词（可多个，全部命中才算）")
    ap.add_argument("-n", type=int, default=20, help="最多显示几处")
    ap.add_argument("-c", type=int, default=2, help="上下文行数")
    ap.add_argument("--lesson", type=int, help="打印某一课全文")
    ap.add_argument("--toc", action="store_true", help="列目录")
    a = ap.parse_args()
    docs = load()

    if a.toc:
        for n, title, _ in docs:
            print("%3d  %s" % (n, title))
        return
    if a.lesson:
        for n, title, body in docs:
            if n == a.lesson:
                print(body)
                return
        sys.exit("没有第 %d 课" % a.lesson)
    if not a.kw:
        ap.print_help()
        return

    kws = [_norm(k) for k in a.kw]
    hits = 0
    for n, title, body in docs:
        lines = body.split("\n")
        for i, ln in enumerate(lines):
            if all(k in _norm(ln) for k in kws):
                hits += 1
                if hits > a.n:
                    print("… 命中过多，只显示前 %d 处（用 -n 调整）" % a.n)
                    return
                lo, hi = max(0, i - a.c), min(len(lines), i + a.c + 1)
                print("─" * 62)
                print("第 %d 课  %s" % (n, title[:60]))
                for j in range(lo, hi):
                    mark = "▶" if j == i else " "
                    print("%s %s" % (mark, lines[j]))
    print("─" * 62)
    print("共 %d 处命中" % hits)


if __name__ == "__main__":
    main()
