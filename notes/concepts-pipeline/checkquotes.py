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

★★ 2026-10-01 05:1x–05:2x（三组统一前，我自己复跑三个文件时又抓出**两条假红**）：
   ③ **尾随省略号被挡**：判据原写 `len(ps) > 1`，「本课，就是把前面“线段破坏的…」这种
      **缩引**（引用者表示「后面还有」）只剩一片 ⇒ 合法引文被判成走样。
      改成：只要含「…」就按片查，并加下限「最长那片 ≥ --min」。放宽的只是
      **省略号可以在末尾**，每一片仍要逐字命中、按序、同一课。
   ④ **「空白归一」档形同虚设**：拿「去过空白的引文」去比「带空白的语料」，几乎从不命中
      ⇒ 所有只差空白的块被**误记进 punct 档**（连『继续说线段的划分』这种没有标点的
      也被报成「仅标点」，当场露馅）。改成比 **去过空白的语料**。
   ⇒ 效果（三组同一把尺，门槛 4）：结构组 不中 12→5、标点 18→0，动力学组 标点 8→4；
     我这份 975 块**一个数没动**（说明这两条没有回头放宽我自己那批）。
   ★ 复算命令：`git show origin/main:docs/concepts/inventory_动力学.md > /tmp/x.md` 再跑本脚本。

★★ 2026-10-01 05:0x 加第六档 **punct（仅标点归一）** —— @iris-64a1 逐条归类自己文件里 60 条
   不中时量出来的：其中 **只有 5 条是纯排版**（全角逗号 vs 语料半角），**其余是真删字/改字**。
   这两件事必须分开报，理由不是「让数好看」，而是**两件事的修法不同**：
   标点差异改一个字符，删改差异要回原课重抄 —— **并成一个数，就会有人为了降一个数去改另一件事**。
   ★ 这一档**只映射标点**（，。；：！？（）等 → 半角），一个汉字/字母/数字都不动；
     按老规矩测过：「会不会把两个不同的字变成同一个」—— 不会。
   ★ **它不放宽门**：punct 与 miss 分列打印、punct 逐条点名，退出码仍只看 miss。
     永远绿的门（atlas 那版渲染期降级）与本档的区别就在这：**这里每一条都印出来给你看**。

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


# 全角标点 → 半角。**只映射标点，一个汉字/字母/数字都不动。**
# 用途：把「纯排版差异」从「真删字改字」里分出来单独报（见下 punct 档）。
PUNCT = str.maketrans({
    "，": ",", "。": ".", "；": ";", "：": ":", "！": "!", "？": "?",
    "（": "(", "）": ")", "、": ",", "【": "[", "】": "]",
    "《": "<", "》": ">", "～": "~", "－": "-", "／": "/",
    "％": "%", "＋": "+", "＝": "=", "＿": "_", "　": " ",
})


def lo(s):
    """归一到底：剥装饰 → 去空白 → 标点全角半角归一。"""
    return re.sub(r"\s+", "", fold(s)).translate(PUNCT)


def hits(q, lessons, folded, lossy, nws, mn):
    """返回 q 落在哪一档：strict / deco / ellipsis / norm / punct / miss。"""
    qs = q.replace("↵", "")
    if any(qs in v for v in lessons.values()):
        return "strict"
    fq = fold(qs)
    if any(fq in v for v in folded.values()):
        return "deco"
    # 带省略号：把非空片按序在同一课里找。
    # ★ 2026-10-01 05:1x 修一条**假红**：以前写成 `if len(ps) > 1`，于是
    #   「本课，就是把前面“线段破坏的…」这种**尾随省略号**（引用者表示「后面还有」）
    #   只剩一片，被挡在门外 ⇒ 一句合法的缩引被判成走样。
    #   ⚠️ 放宽的只是「省略号可以在末尾/开头」；每一片仍然要**逐字命中、按序、同一课**，
    #     再加一条下限：最长的那片至少 --min 字 —— 免得「…」这种空壳蒙混过关。
    if "…" in fq:
        ps = [p for p in re.split(r"[…]+", fq) if p]
        if ps and max(len(p) for p in ps) >= mn:
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
    # 空白不敏感档。★ 比的是**去过空白的语料**（nws），不是原语料 ——
    #   2026-10-01 05:2x 修：以前拿「去过空白的引文」去比「带空白的语料」，
    #   这一档几乎从不命中，于是所有只需去空白的块都被**误记进 punct 档**
    #   （连『继续说线段的划分』这种一个标点都没有的也被报成「仅标点」，当场露馅）。
    if any(re.sub(r"\s+", "", fq) in v for v in nws.values()):
        return "norm"
    # ★ 最后一档：只有标点符号不同（全角/半角）——**单独报**，不混进 miss。
    #   iris 2026-10-01 逐条归类时把这一类量出来是「纯排版」，和「真删改」是两回事；
    #   两件事一个数报，就会有人为了降一个数去改另一件事。
    if any(lo(qs) in v for v in lossy.values()):
        return "punct"
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
    lossy = {k: lo(v) for k, v in lessons.items()}
    nws = {k: re.sub(r"\s+", "", v) for k, v in folded.items()}

    quotes = [m.group(1) for m in re.finditer("「([^「」]*)」", text)
              if len(m.group(1)) >= mn]
    bucket = {"strict": [], "deco": [], "ellipsis": [], "norm": [], "punct": [], "miss": []}
    for q in quotes:
        bucket[hits(q, lessons, folded, lossy, nws, mn)].append(q)

    print("%s ｜ 门槛 ≥%d 字 ｜ 尺：单课整块逐字 ＋ 双侧剥装饰(↵ ** 各式引号) ＋ 省略号按序切片" % (path, mn))
    print("「」块 %d ｜ 原样逐字 %d ｜ 剥装饰后 %d ｜ 省略号按序 %d ｜ 仅空白归一 %d ｜ 仅标点归一 %d ｜ 都不中 %d"
          % (len(quotes), len(bucket["strict"]), len(bucket["deco"]),
             len(bucket["ellipsis"]), len(bucket["norm"]), len(bucket["punct"]),
             len(bucket["miss"])))
    print("★ 只有『仅标点归一』和『都不中』是要看的；前四档是干净的。"
          "标点档＝纯排版（全角/半角标点），删改档＝真的少字/改字 —— 两件事分开数。")
    for q in bucket["norm"]:
        print("  ~ 需空白归一：", q[:80])
    for q in bucket["punct"]:
        print("  · 仅标点：", q[:80])
    for q in bucket["miss"]:
        print("  ✗ 不中：", q[:80])
    print("含 ↵ 折行 %d ｜ 含省略号 %d" % (sum("↵" in q for q in quotes),
                                       sum("…" in q for q in quotes)))
    return 1 if bucket["miss"] else 0


if __name__ == "__main__":
    sys.exit(main())
