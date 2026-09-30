# -*- coding: utf-8 -*-
"""全仓「」普查：**每一个**「…」/『…』配对都拿去 108 课原文核，按位置出四格。

用法：
    python3 tools/quotes_census.py
    QL_REPO=<另一棵树> python3 tools/quotes_census.py
    QL_CORPUS=<含 archive/chanlun108/text 的树> python3 tools/quotes_census.py

退出：
    0  跑完，且 B「找不到」= 0
    1  跑完，但有 B「找不到」
    2  **语料不在，什么都没查** —— 查不了 ≠ 通过（跟 verify_quotes.py 同一条规矩）

⚠ 退出码只答 B，**不答 C**：C（短·判不了）在每一次跑里都是几百处，若把它塞进 rc
  那 rc 就永远恒等于 1、等于没有 rc。C 只印在报告里，且印在 B 的**紧邻处**，
  读的人一眼能看到"这个 0 旁边还有 199 处没人判过"。**rc 的分辨力是有限的，
  让它去答它答不了的问题 = 把一条通道用废。**

=========================== 这支器和 verify_quotes.py 的关系 ===========================
**它不重写口径，它 import 那一支。** `norm()` / `fold()` / `split_ellipsis()` /
`Corpus.chain_in()` / `load()` / `fingerprint()` / `SKIP` 全部从
`tools/verify_quotes.py` 复用（`import verify_quotes as V`）。理由：
同一件事有两支各写一遍的判据，两支迟早会分家，而分家的那天没人会红。
## ⚠ 更正（2026-09-30 11:5x，卡 `card-082d9aaa-cbb`）：这里原来写「只差分母」—— **不对**

对的那半留着：本器**不重写口径**，`norm/fold/split_ellipsis/chain_in/load/fingerprint/SKIP`
全部 `import verify_quotes as V` 复用。同一件事两支各写一遍，迟早分家，分家的那天没人会红。

写错的那半。本器跟**卡面那支 `count_quotes.py`** 差**四样**，不只是分母（四样都实测过）：

```
                        卡面 count_quotes.py              本器
① 单位（★最关键）       只数**「在原文里找不到」的配对**     数**每一个**配对，分 A/B/C 三箱
                          ⇒ cards/ 78                        ⇒ cards/ 全配对 181、B 找不到 34
② 阶梯档数              只接 `norm` 一档                    接六档（含「逐段核（省）」）
                          ⇒ 忠实省略号引文落进"找不到"          ⇒ 那些被救回 A 档
                          实测差额：cards 78→68 · core+render 57→50 · tools 182→179
③ 扫描面                只扫 .py，只跳 .git/archive           扫 .py/.md/...，跳 verify_quotes 的 SKIP
                          （**含** tools/v1_ref）             （**跳** tools/v1_ref）
④ 短配对                （无这一箱）                          norm < 6 字单列成 C，**不进 B**
```

⇒ **四样里任意一样变了，数就变。** 本器的 B 列与卡面那四格**不是同一个量**：
   不许相加、不许互相顶替，也**不许拿一支去否另一支**（参照实现不在手边时只能说"无法证伪"）。

    verify_quotes.collect()  只收**带课号的引文**（`:161` 起，`if not cites: continue`）
                             ⇒ 它的分母是"我们标了出处的那部分"，不是全仓
    本器                     收**每一个**配对，**不要求带课号**

## ★ 还有一根轴：`norm` 是哪一版 —— 但别记 blob，记这一行内容

卡面那四格**只在一种 `norm` 下对得上**：`PUNCT` 字符集里**有一个字面的 `*`**
（那是 `51b377f`「归一化掉 markdown 的 `*`」加进去的）。换回甲1 之前的 `norm`，
加粗的真引文会变成"搜不到" ⇒ `core+render 57→60 · tools 182→184`，又一轮"复现不出"。

**坐标不许写成 blob。** 实测（`05f3e24..origin/main` 区间内 + `05f3e24` 共 38 笔）：
`tools/verify_quotes.py` 出现过 **6 个 blob**（`23274277 · 2a77483d · 717265f7 ·
93fbf2ad · 9c9380e0 · b31431b3`），按谓词只切**两**类。也就是说
**blob 与谓词 N:M、两个方向都不一对一**：四个不同 blob（`23274277`/`2a77483d`/
`717265f7`/`93fbf2ad`）共用同一份谓词区；照 blob 核对会因为别人追加一个不相干的
函数就宣布"仪器变了、得复算"——那是**虚警**。

一行内容判（**不依赖行号**：`PUNCT =` 在两版里是第 73 行 vs 第 90 行，钉行号的命令换一笔就错）：

```
git cat-file -p <blob> | grep "^PUNCT = "        # 或 git show <树>:tools/verify_quotes.py | …
# 卡面那一档应有的样子：那一行字符集的收尾是 `【】` + 一个星号 + 反斜杠-s，
#   即 【】 与空白类之间**有一个字面的 `*`** —— 它是字符，不是量词。
#   norm 行里**不出现 ELL**（ELL 只进 split_ellipsis，见下）。
```

快筛（等价但**非结构性蕴含**，别拿它当唯一判据）：`git merge-base --is-ancestor 51b377f <树>`。
我把这 38 笔逐笔比过 `is-ancestor` 与"含字面 `*`"，**反例 0** —— 但 0 反例的理由是那几个
"无*"全是甲1 之前的**支尖**、每次 merge 都是 main 那侧赢；**哪次解析成旧档，这条线当场断**。
⇒ 快筛用祖先，**真值用内容**。

同一族的两条实测（同一次审计，配合 `tools/quotes_recount.py --unit gone`）：

```
                          cards   core+render   tools
  norm · 一档（卡面）        78        57        182
  norm + 逐段核（省）         68        50        179     ← −10/−7/−3 全在这一档
  norm_ell · 一档             73        56        186     ← 假想：把 ELL 也接进 norm ⇒ −5/−1/**+4**（反向）
  norm_ell + 逐段核（省）      68        50        183
```

⇒ **验收基准必须连"阶梯"一起报**：两套都跑得出，写哪套都行，但不写就会有人拿 A 套的基准核 B 套的读数。
⇒ **`ELL` 不是第二根轴**：它只被 `split_ellipsis()` 用（就是「逐段核（省）」那一档），
   所以它在那根轴**里面**。把它接进 `norm` 走的是 −5/−1/+4，不是 −10/−7/−3。

=================================== 为什么要有这支 ================================
小栋 08:5x 拍「A：引号只给原文用」。要验收「改完了没」，得有一个**别人也能跑**的
分母 —— 而卡面当时引的方法是 `workspace/count_quotes.py`：
**那个文件不在本仓任何一次提交里**（`git log --all --diff-filter=A` 空）。
活在某一个人的家目录里的脚本 = 判据不可复算 ⇒ 数再多也不能当验收。

=================================== 分档（照抄 verify_quotes 的阶梯） ================================
    严档命中   逐字原样 / 折叠叠字后 / 规范化后          ← 由 V.hunt 同构地跑
               截单段 / 逐段·折叠 / 逐段·规范            ← 由 V.split_ellipsis + V.Corpus.chain_in
    太短        norm(配对) < 6 个字                      ← **单列，不并进"找不到"**
    找不到      以上都不中                               ← 就是卡面要数的那个数

「太短」为什么要单列：7 个字对任何一课都近乎必然命中（verify_quotes.py 文件头原话），
所以**短配对的"命中"是假命中**；但反过来，短配对的"**没**命中"也不是编造的证据 ——
它可能只是一句 4 个字的常用词。这一档**两个方向都不可读**，只能点名，不能计数。
（本器不判 LOOSE 那三档：那三档在 verify_quotes 里的用途是"未定性"，不是"对上"。）
"""
import ast, io, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_quotes as V                                   # noqa: E402  —— 复用，不重写

REPO = V.REPO
SHORT = 6                       # norm 后短于这个长度 ⇒ 「太短」，两个方向都不可读

# 只扫"我们能读的文本载体"。二进制/图片/字体不在分母里 —— 它们本来就没有引号。
TEXT_EXT = (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".sh")

QPAT = re.compile(r"「([^「」]{1,300}?)」|『([^『』]{1,300}?)』", re.S)

# ============================ 先拼字面量，再找引号 ============================
# 仓里的引文几乎都长这样（`cards/c07_level.py:47` 实测）：
#     d.text((x, y), "「再次强调！……没有任何必然关系，"
#                    "……」", font=f_t)
# 一句引文被**相邻字面量**切成两半。抓原文的如果是"整篇正则扫一遍"，
# 那个「」配对中间就夹着 `",\n        "` 这样的源码碎片 ⇒
# **一条完全忠实的引文被判成"找不到"**（@iris-64a1 ⑧ 那条讲的就是它，
# 她数出 17 处这种假象）。所以本器先把相邻字面量**拼回一句**再找引号。
#
# ⚠ 代价要说清楚：拼接后的字符下标不再和源码一一对应 ⇒ 位置只能记成
# **这一串字面量里第一段的行号**。"在某一行出现"是弱主张，"行号精确"是强主张，
# 本器给的是前者，不冒充后者。
LIT = re.compile(
    r"(?:[rbfuRBFU]{0,2})(?:"
    r'"""(?:[^"\\]|\\.|"(?!""))*"""'
    r"|'''(?:[^'\\]|\\.|'(?!''))*'''"
    r'|"(?:[^"\\\n]|\\.)*"'
    r"|'(?:[^'\\\n]|\\.)*'"
    r")")
GAP = re.compile(r"^[\s]*(?:\+[\s]*)?$", re.S)      # 相邻字面量之间只允许空白/换行/一个 +


def sh(*a):
    try:
        return subprocess.run(a, cwd=REPO, capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        return "?"


def chunks(rel, text):
    """产出 (可扫文本, 源码偏移, 是不是拼接出来的)。.py 走字面量拼接，其余整篇一层。"""
    if not rel.endswith(".py"):
        yield text, 0, False
        return
    ms = list(LIT.finditer(text))
    if not ms:
        yield text, 0, False
        return
    i = 0
    while True:
        j = i + 1
        while j < len(ms) and GAP.match(text[ms[j - 1].end():ms[j].start()]):
            j += 1
        run = ms[i:j]
        parts = []
        for m in run:
            try:
                v = ast.literal_eval(m.group(0))
            except Exception:                      # f-string 带占位符等 ⇒ 原样
                v = m.group(0)
            if isinstance(v, bytes):
                v = v.decode("utf-8", "ignore")
            if not isinstance(v, str):
                v = m.group(0)
            parts.append(v)
        yield "".join(parts), run[0].start(), len(run) > 1
        nxt = ms[j].start() if j < len(ms) else len(text)
        yield text[run[-1].end():nxt], run[-1].end(), False   # 字面量之外的注释/代码也扫
        if j >= len(ms):
            return
        i = j


def top(rel):
    """按位置分格：一级目录名；根下的散文件按文件名。"""
    parts = rel.split(os.sep)
    return os.path.dirname(rel) or parts[0] if len(parts) == 1 else parts[0] + "/"


def walk():
    """产出 (相对路径, 文本)。SKIP 直接复用 verify_quotes 的那份 —— 别抄第二份。"""
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs
                   if not any(os.path.join(root, d).endswith(s) or d == s
                              for s in ("__pycache__",) if True)]
        if any(("/%s" % x.split("/")[-1]) in root or root.endswith(x)
               for x in V.SKIP):
            continue
        for f in sorted(files):
            if not f.endswith(TEXT_EXT):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO)
            if any(rel == x or rel.startswith(x + os.sep) for x in V.SKIP):
                continue
            try:
                yield rel, io.open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue                                     # 读不了的，不装成 0


def classify(q, docs, corps):
    """返回 (档位, 课号列表)。documents 里的五档之外只回 '找不到'。"""
    c_raw, c_fold, c_norm = corps
    for how, needle in (("逐字原样", q), ("折叠叠字后", V.fold(q)),
                        ("规范化后", V.norm(q))):
        hits = c_raw.where(needle) if how == "逐字原样" else \
            (c_fold.where(needle) if how == "折叠叠字后" else c_norm.where(needle))
        if hits:
            return how, hits
    segs, kind = V.split_ellipsis(q)
    if segs:
        for tag, corp, xf in (("截单段", c_raw, lambda s: s),
                              ("逐段·折叠", c_fold, V.fold),
                              ("逐段·规范", c_norm, V.norm)):
            hits = [j for j in range(len(docs))
                    if corp.chain_in([xf(p) for p in segs], j)]
            if hits:
                return tag, sorted(corp.nums[j] for j in hits)
    return "找不到", []


def main():
    docs = V.load()
    if docs is None:
        print("=" * 84)
        print("语料查不了 —— **什么都没查**，这一条不是「通过」")
        print("=" * 84)
        print("  找的是：%s" % V.txt_dir())
        print("  先跑：python3 tools/fetch_chanlun108.py")
        print("  或指到已有的那份：QL_CORPUS=<树> python3 tools/quotes_census.py")
        print("退出原因: 语料不在 ⇒ exit=2")
        return 2

    fp, nbytes = V.fingerprint(docs)
    corps = (V.Corpus(docs, lambda s: s), V.Corpus(docs, V.fold),
             V.Corpus(docs, V.norm))

    rows = {}          # 格 -> 计数
    uniq = {}          # 格 -> {norm键: (配对, 档, 位置)}
    joined, multi, n_pair = [], [], 0
    for rel, text in walk():
        cell = top(rel)
        for chunk, off, is_join in chunks(rel, text):
            for m in QPAT.finditer(chunk):
                q = m.group(1) or m.group(2)
                k = V.norm(q)
                n_pair += 1
                how, hits = classify(q, docs, corps)
                if how == "找不到" and len(k) < SHORT:
                    how = "太短"
                ln = text.count("\n", 0, off + m.start()) + 1
                where = "%s:%d" % (rel, ln)
                if is_join:
                    joined.append("%s  「%s」" % (where, q.replace("\n", "\\n")[:56]))
                if "\n" in q:
                    multi.append(where)
                r = rows.setdefault(cell, dict(pair=0, gone=0, short=0, uniq=set(),
                                               ugone=set(), ushort=set()))
                r["pair"] += 1
                r["uniq"].add(k)
                if how == "找不到":
                    r["gone"] += 1
                    r["ugone"].add(k)
                elif how == "太短":
                    r["short"] += 1
                    r["ushort"].add(k)
                uniq.setdefault(cell, {}).setdefault(k, (q, how, where))

    print("=" * 84)
    print("全仓「」普查 —— 每一个配对拿去 108 课原文核（不要求带课号）")
    print("=" * 84)
    print("量法   一个「…」/『…』配对算一处；去重键 = verify_quotes.norm(配对)")
    # 空坐标不许印成空格：被审计的树不是 git 仓时，"@ " 后面那截空白
    # 和"某个 sha"在同一次扫读里长得一样 ⇒ 明写「非 git 树」。
    head, tree = sh("git", "rev-parse", "HEAD")[:12], sh("git", "rev-parse",
                                                         "HEAD^{tree}")[:12]
    print("对象   %s @ %s" % (REPO, head or "(非 git 树 —— 坐标取不到)"))
    if tree:
        print("       树 %s" % tree)
    print("语料   sha256:%s   %d 课 / %.1f MB" % (fp, len(docs), nbytes / 1048576.0))
    print("判据   tools/verify_quotes.py 自己的 norm/fold/split_ellipsis/chain_in"
          "（import 复用，未重写）")
    print("归属   **纯路径**：相对仓根的一级目录名；根下的散文件按文件名。"
          "没有\"被谁调用算谁的\"那一层 ——")
    print("       谁想跟我对数，先报这两样：分母（配对总数）＋ 归属规则。"
          "总数一样而桶不一样 ⇒ 差的是归属，不是计数")
    print()
    print("★ 三箱，不许并：A 严档命中（=原文）· B 找不到（=我们的字，要改）· "
          "C 短·判不了（**两个方向都不可读**）")
    print()
    print("%-16s %6s %6s %8s %6s %8s %8s"
          % ("位置", "配对", "去重", "A严档命中", "C短·判不了", "B找不到", "B去重"))
    print("-" * 84)
    tot = dict(pair=0, uniq=0, ok=0, short=0, gone=0, ugone=0)
    for cell in sorted(rows, key=lambda c: -rows[c]["pair"]):
        r = rows[cell]
        ok = r["pair"] - r["gone"] - r["short"]
        print("%-16s %6d %6d %8d %6d %8d %8d"
              % (cell, r["pair"], len(r["uniq"]), ok, r["short"],
                 r["gone"], len(r["ugone"])))
        tot["pair"] += r["pair"]; tot["uniq"] += len(r["uniq"]); tot["ok"] += ok
        tot["short"] += r["short"]; tot["gone"] += r["gone"]
        tot["ugone"] += len(r["ugone"])
    print("-" * 84)
    print("%-16s %6d %6d %8d %6d %8d %8d"
          % ("合计", tot["pair"], tot["uniq"], tot["ok"], tot["short"],
             tot["gone"], tot["ugone"]))

    # ⚠ 「去重」这一列**不是各格去重之和**：同一个 norm 键出现在两个格时，
    #   各格各算一次、合计也各算一次 ⇒ 合计 ≥ 真·全局去重。这行印的是**真**值。
    g = {}
    for c, d in uniq.items():
        for k, v in d.items():
            g.setdefault(k, v)
    print()
    print("★ 全局去重（跨格合并）%d 条 —— 比上面那列之和少 %d，"
          "差额 = 同一句出现在多个格里的次数" % (len(g), tot["uniq"] - len(g)))

    print()
    print("★ 排除项（点名，不折进任何总数）：")
    print("  本器没量：扩展名不在 %s 里的文件（图片/字体/二进制本来就无引号）"
          % " ".join(TEXT_EXT[:5]))
    print("  跳过目录：%s" % " ".join(V.SKIP))
    # 量器自己也在被量的树里 —— 这两支的文件头全是「」例子。**不静默排除**：
    # 排除会让"我改一行工具 ⇒ 数不动"变成一句我替读者做的判断。印出来，让读的人自己减。
    for f in ("tools/quotes_census.py", "tools/verify_quotes.py"):
        n = sum(1 for rel, t in walk() if rel == f
                for ch, _o, _j in chunks(rel, t) for _m in QPAT.finditer(ch))
        if n:
            print("  ⚠ 量器自己在被量的树里占 %d 处（%s）—— 改那一支，总数会跟着动"
                  % (n, f))
    print("  跨行配对 %d 处（同一次审计里 verify_quotes 的 `multiline` 只认带课号那部分）"
          % len(multi))
    print("  由**相邻字面量拼回来**的配对 %d 处 —— 不拼的话它们中间夹着 `\",\\n\"`，"
          "会被逐字档判成取不到（@iris-64a1 ⑧ 数的是同一件事）：" % len(joined))
    for x in joined[:15]:
        print("      %s" % x)
    if len(joined) > 15:
        print("      …（另 %d 处）" % (len(joined) - 15))

    print()
    if tot["gone"] == 0:
        print("退出原因: B「找不到」0 处 ⇒ exit=0（C「短·判不了」%d 处仍要人来判，"
              "但**不并进 B**）" % tot["short"])
        return 0
    print("退出原因: B「找不到」%d 处（去重 %d 条）· C「短·判不了」%d 处 "
          "（**两个方向都不可读，不并进 B，也不并进 A**）⇒ exit=1"
          % (tot["gone"], tot["ugone"], tot["short"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
