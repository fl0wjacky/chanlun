# -*- coding: utf-8 -*-
"""逐字自检：把清单里每个「」引文块拿回语料核 —— 抄走样（如 关于/关於）会在这里现形。

用法（在 wt-concepts worktree 根跑）：
    python3 checkquotes.py [文件路径] [--min 4]

★ 门槛默认 4。以前默认 25 会把**短引文**的漂移整片漏掉 —— 2026-10-01 nova 用低门槛
  扫出我新加段落里 45 处「」不是语料逐字（如把「必须保证中枢的确立」写成「先保证中枢的确立」）。
  报数时必须连门槛一起报。

★★ 2026-10-01 05:2x 修两个**假红**（nova 用本脚本扫 atlas 的文件时暴露；95 条不中里
   大部份是脚本自己造的，不是他文件的问题）：
   ① **不去 Markdown 加粗**：引文里写了 `**处理**`，语料是「处理」——不剥掉星号必然判不中。
   ② **带「…」的块整块比对**：块里有省略号时整块本来就不可能命中，旧版只把它们
      单独计数（「含省略号 N 块」）就算交代过去了 —— 那是偷懒。
   ⇒ 现在剥 `**`、并把 `…` 切成若干片，要求**每一片按序命中同一课**。
   ★ 这两条**只去掉假红、不放宽门**：切出来的每一片仍然要逐字节命中，漏字/改字照样红。
     报数分档打印，谁都能看见每一档降了多少 —— 不允许出现「静默降级」那种永远绿的门。

★ 用法坑：`sys.argv` 里 `--min` 后面的数字会被当成路径，**必须显式传文件路径**：
    python3 checkquotes.py docs/concepts/inventory_中枢走势组.md --min 4

尺（报数时必须连尺一起报）：
  · 只收「」块，长度 ≥ --min
  · 先剥掉折行标记 ↵，再要求**整块**在某**一课**的合并文本里逐字命中
    —— 每课各自去换行后匹配，**不跨课拼接**（拼了会造出假命中）
  · 分档报：原样 / 剥加粗 / 省略号按序 / 只靠空白归一 / 都不中

来源：atlas-791f 2026-10-01 在 card-c4e6b9d4-5ad 报出他在自己文件里把
语料的「关於」手打成「关于」（两处）—— 手打引文就是会走样。这份是我在
自己成品上按同一把尺重核用的脚本（当时结果：174/174 命中、0 需归一）。
"""
import re, sys, glob

# 只剥**装饰**（加粗星号、各式引号：半角/全角/中日式），**不剥任何正文内容**。
# 判据：两边的差异必须只是「同一串字被什么样的符号装饰」；凡是会吃掉正文字符的
# 变换一律不许加进来 —— 加了就是「静默降级」，门就永远绿了。
DECOR = str.maketrans("", "", "**\"'“”‘’「」『』")


def fold(s):
    """剥折行标记 ＋ 装饰符（双侧都剥）。"""
    return s.replace("↵", "").translate(DECOR)


def hits(q, lessons, folded):
    """返回 q 落在哪一档：strict / deco / ellipsis / norm / miss。"""
    qs = q.replace("↵", "")
    if any(qs in v for v in lessons.values()):
        return "strict"
    fq = fold(qs)
    if any(fq in v for v in folded.values()):
        return "deco"
    ps = [p for p in re.split(r"[…]+", fq) if p]
    if len(ps) > 1:                       # 带省略号：每片按序命中**同一课**
        for v in folded.values():
            pos, ok = 0, True
            for p in ps:
                j = v.find(p, pos)
                if j < 0:
                    ok = False
                    break
                pos = j + len(p)
            if ok:
                return "ellipsis"
    if any(re.sub(r"\s+", "", fq) in v for v in folded.values()):
        return "norm"
    return "miss"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "docs/concepts/inventory_中枢走势组.md"
    mn = 4
    if "--min" in sys.argv:
        mn = int(sys.argv[sys.argv.index("--min") + 1])

    text = open(path, encoding="utf-8").read()
    lessons = {f: open(f, encoding="utf-8").read().replace("\r", "").replace("\n", "")
               for f in sorted(glob.glob("archive/chanlun108/text/lesson-*.txt"))}
    folded = {k: fold(v) for k, v in lessons.items()}

    quotes = [m.group(1) for m in re.finditer("「([^「」]*)」", text)
              if len(m.group(1)) >= mn]
    bucket = {"strict": [], "deco": [], "ellipsis": [], "norm": [], "miss": []}
    for q in quotes:
        bucket[hits(q, lessons, folded)].append(q)

    print("%s ｜ 门槛 ≥%d 字 ｜ 尺：单课整块逐字 ＋ 双侧剥装饰(↵ ** 各式引号) ＋ 省略号按序切片" % (path, mn))
    print("「」块 %d ｜ 原样逐字 %d ｜ 剥装饰后 %d ｜ 省略号按序 %d ｜ 仅空白归一 %d ｜ 都不中 %d"
          % (len(quotes), len(bucket["strict"]), len(bucket["deco"]),
             len(bucket["ellipsis"]), len(bucket["norm"]), len(bucket["miss"])))
    for q in bucket["norm"]:
        print("  ~ 需归一：", q[:80])
    for q in bucket["miss"]:
        print("  ✗ 不中：", q[:80])
    print("含 ↵ 折行 %d ｜ 含省略号 %d" % (sum("↵" in q for q in quotes),
                                       sum("…" in q for q in quotes)))
    return 1 if bucket["miss"] else 0


if __name__ == "__main__":
    sys.exit(main())
