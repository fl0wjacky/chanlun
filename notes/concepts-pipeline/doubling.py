# -*- coding: utf-8 -*-
"""叠字统计（语料噪声）—— 两个口径分开报，别合成一个数。

用法（在 wt-concepts worktree 根跑）：
    python3 doubling.py

口径：
  · 通用档：正则 ([\\u4e00-\\u9fff])\\1 ＝「相邻两个相同汉字」
      - **单行尺**（在原始文本上跑，默认）：折行处不会撞出假叠字
      - 去折行尺会把**行尾／行首同字**撞成假的（实测全库 2243 → 2251，多 8 处）
  · 虚词档：通用档里**只留虚词**的命中 ＝ 疑似 OCR 重字
      - 通用档里绝大多数是**正常叠词**（好好看／往往／谢谢／慢慢），必须减掉

来源：2026-10-01 三组共用口径 —— atlas 报「40 课／242 行」因没写匹配规则、复现不出来而作废；
重跑通用档得 103 课／2243 处／1199 行（单行尺）。虚词档是我切的那一刀。
"""
import re, glob, collections

STOP = set("的是就而和了在也有一不中那这我你他们与或从对到把被又还都很将会能可要只更再没于其")
PAT = re.compile(r"([一-鿿])\1")
FILES = sorted(glob.glob("archive/chanlun108/text/lesson-*.txt"))


def report(name, keep):
    lessons = set(); occ = 0; lines = 0; cnt = collections.Counter()
    for f in FILES:
        n = int(re.search(r"lesson-(\d+)", f).group(1))
        raw = open(f, encoding="utf-8").read().replace("\r", "")
        hits = [m.group(1) for m in PAT.finditer(raw) if keep(m.group(1))]
        hl = [l for l in raw.split("\n") if any(keep(m.group(1)) for m in PAT.finditer(l))]
        if hits: lessons.add(n)
        occ += len(hits); lines += len(hl); cnt.update(hits)
    print("%s ｜ 课 %d ｜ 处 %d ｜ 行 %d ｜ top: %s"
          % (name, len(lessons), occ, lines, " ".join("%s%d" % kv for kv in cnt.most_common(6))))


if __name__ == "__main__":
    report("通用档·单行尺", lambda c: True)
    report("虚词档·单行尺（疑 OCR）", lambda c: c in STOP)
    # 去折行尺，只为量「折行撞出的假叠字」有多少
    raw_all = "".join(open(f, encoding="utf-8").read().replace("\r", "") for f in FILES)
    print("去折行尺 通用档 处 %d（与单行尺之差＝折行假叠字）" % len(PAT.findall(raw_all.replace("\n", ""))))
