# -*- coding: utf-8 -*-
"""逐字自检：把清单里每个「」引文块拿回语料核 —— 抄走样（如 关于/关於）会在这里现形。

用法（在 wt-concepts worktree 根跑）：
    python3 checkquotes.py [文件路径] [--min 4]

★ 门槛默认 4。以前默认 25 会把**短引文**的漂移整片漏掉 —— 2026-10-01 nova 用低门槛
  扫出我新加段落里 45 处「」不是语料逐字（如把「必须保证中枢的确立」写成「先保证中枢的确立」）。
  报数时必须连门槛一起报。

尺（报数时必须连尺一起报）：
  · 只收「」块，长度 ≥ --min（默认 25 字，Atlas 那把尺同值）
  · 先剥掉折行标记 ↵，再要求**整块**在某**一课**的合并文本里逐字命中
    —— 每课各自去换行后匹配，**不跨课拼接**（拼了会造出假命中）
  · 严格档（逐字节）与「空白归一」档**分开报**：需要靠归一才中的块，
    说明两边的尺不同（语料写「本 ID 理论」带空格）—— 那一档要单独看，别混进"命中"。

来源：atlas-791f 2026-10-01 在 card-c4e6b9d4-5ad 报出他在自己文件里把
语料的「关於」手打成「关于」（两处）—— 手打引文就是会走样。这份是我在
自己成品上按同一把尺重核用的脚本（当时结果：174/174 命中、0 需归一）。
"""
import re, sys, glob


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "docs/concepts/inventory_中枢走势组.md"
    mn = 4
    if "--min" in sys.argv:
        mn = int(sys.argv[sys.argv.index("--min") + 1])

    text = open(path, encoding="utf-8").read()
    lessons = {f: open(f, encoding="utf-8").read().replace("\r", "").replace("\n", "")
               for f in sorted(glob.glob("archive/chanlun108/text/lesson-*.txt"))}
    nw = lambda s: re.sub(r"\s+", "", s)
    cn = {k: nw(v) for k, v in lessons.items()}

    quotes = [m.group(1) for m in re.finditer("「([^「」]*)」", text)
              if len(m.group(1)) >= mn]
    strict, norm, miss = [], [], []
    for q in quotes:
        qs = q.replace("↵", "")
        if any(qs in v for v in lessons.values()):
            strict.append(q)
        elif any(nw(qs) in v for v in cn.values()):
            norm.append(q)
        else:
            miss.append(q)

    print("%s ｜ 门槛 ≥%d 字" % (path, mn))
    print("「」块 %d ｜ 严格逐字命中 %d ｜ 仅空白归一后命中 %d ｜ 都不中 %d"
          % (len(quotes), len(strict), len(norm), len(miss)))
    for q in norm:
        print("  ~ 需归一：", q[:80])
    for q in miss:
        print("  ✗ 不中：", q[:80])
    print("含 ↵ 折行 %d ｜ 含省略号 %d" % (sum("↵" in q for q in quotes),
                                       sum("…" in q for q in quotes)))
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
