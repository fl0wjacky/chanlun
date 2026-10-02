# -*- coding: utf-8 -*-
"""把仓库里每一条「引文」拿去 108 课原文核，并和仓库自己标的那几课对。

用法：
    python3 tools/verify_quotes.py            # 审计本仓
    QL_REPO=<另一棵树> python3 tools/verify_quotes.py
    QL_CORPUS=<含 archive/chanlun108/text 的树> python3 tools/verify_quotes.py

退出：
    0  跑完且 ①②③ 全空
    1  跑完，但有 ② 课号不符 / ③ 搜不到
    2  **语料不在，什么都没查** —— 查不了 ≠ 通过，别把它读成 0

================================ 口径 ================================
不"行内就近配对"：一行里可能同时出现两三个课号，就近配对会把引文挂到错的课号上
（第一版抽取器就犯了这个错）。改成**按引文找**：
  · 原文那边：这句出现在哪几课             → 事实
  · 仓库那边：这句出现在哪些行、那些行上出现过哪些课号 → 仓库的声称
  · 判：声称里有没有事实。没有 → ②；事实为空 → ③。

**⚠ 「共 N 条」是尺的产物，不是语料的属性**：
N 是**去重后**的引文数，键 = `norm(引文)` ⇒ **谁改 `norm`，谁就在改分母**。
出过一次：把 markdown 的 `*` 归一化掉，两条只差星号的引文**合成一个 key**
⇒ 总数 152 → 151，而 ③ 只少 1 条。**"分类动了"和"母体动了"是两件事，
只看 ③ 的增减会把后者漏掉。**报任何比例（如「③ 占 N 的比例」）都要连
`norm` 一起报，否则那个分母不可复算。

**基线（2026-10-02，语料指纹 `cc27e258cdd52eab`）**：
    共 941 条 = ① 598 ＋ ② 168 ＋ ③ 175 ｜ 其中严档 587、④ 退短词 11
    改前是 951 = ① 602 ＋ ② 171 ＋ ③ 178 ｜ 严档 480、④ 122 —— 差的那 10 条是
    `norm` 归一后撞成同一个 key（见下面 `PUNCT` 那段的 `↵`），**不是丢了引文**。
    **引号相关的卡拿这 941 当基线**；换了语料或动了 `norm`，这条先重印一遍再比。

**① 必须分档，且「退短词」不算「对上」**：
   逐字原样 / 折叠叠字后 / 规范化后 / 逐段核（省）   ← 严档，算"对上"
   首尾短词 / 中段短词 / 首 7 字                     ← **未定性**，不能并进"对上"
7 个字对任何课都近乎必然命中，那一档等于没测；把它和"对上"印在同一个数字下，
读的人会以为引文审计比实际干净。**这条是被人逮到过的 bug，别再犯。**

**「逐段核（省）」这一档是补的，补之前仪器在撒谎**：
仓内的合规写法是「原文……省略号」（先例 `cards/c05_center.py:207`），
省略号是**我们插的** ⇒ 这一整串在原文里按构造永远逐字搜不到。
旧版把它和真编造的引文一起丢进「③ 搜不到」，于是**一条合规的引文和一条假引文不可区分**。

⚠️ 这里原来写的是"语料里一个「……」都没有（108 课实测 0 处）"—— **那句是错的，已改**。
双省略号在源文里**有 6 处 / 5 课**（020/022/028/047×2/075）。先前那个 0 是在**折叠后**的
语料上量的：`……` 就是两个相邻同字，而 `fold()` 的 `(.)\1+ → \1` 正好把它吃掉（6 → 0）。
**测「省略号是单是双」时不能过 fold/norm** —— 那个让 OCR 引文变得可核的函数，
同时把这个区分整个抹掉了。⇒ 本档的必要性不在"源文没有双省略号"，
而在"**我们插的省略号**使整串非逐字"；**来源（源文自带 vs 我们加的）只能按位置判**：
逐字命中 ⇒ 源文自带，只逐段命中 ⇒ 我们加的。别按单/双判。
口径（由 @nova-8980 写死）：**省略号只准出现在段与段之间，每一段都必须逐段对上，
错一段就是假引文。** 本档要求各段命中落点**交集非空**（同一课），不是"每段各自在某课出现过"。

**为什么单独留「逐字原样」这一档**：仓里的引文是给人读的，人照抄去 grep。
语料是 OCR 抓的，108 课里 105 课带**相邻同字重复**（「想想了想」「属於」），
所以逐字命中率必然低 —— **低不是错误，没标出来才是**。

================================ 语料指纹（为什么必须印） ================================
本仓 **不跟踪语料**：`.gitignore` 里有 `archive/chanlun108/`，那 1.7M 是
`tools/fetch_chanlun108.py` 从 https://www.furleader.cn/ 抓下来的本地产物。
⇒ "语料可复算"是**有条件的**（源站还得吐同样的字节），不是自动的。
⇒ 所以每份报告都印**语料指纹**：源站哪天改一个字，数会静默地变，
   **没有任何门会红**；印了指纹，至少事后追得回"这 153 个数是哪份语料算的"。
（同一课：「不带字体的数不可读」，换到语料轴上照样成立。）
"""
import io, os, re, sys, bisect, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # 仓根：tools/ 的上一级

# 被审计的代码：默认本仓（也可以指另一棵树，比如待合的分支）
REPO = os.environ.get("QL_REPO") or ROOT
# 语料：默认也在本仓（<= 抓取脚本的落点），可指向别处
CORPUS = os.environ.get("QL_CORPUS") or ROOT

TXT_REL = os.path.join("archive", "chanlun108", "text")
SKIP = (".git", "archive", "out", "__pycache__", "tools/v1_ref")

STRICT = ("逐字原样", "折叠叠字后", "规范化后", "逐段核（省）", "逐段·折叠", "逐段·规范")
LOOSE = ("首尾短词", "中段短词", "首 7 字")

ELL = re.compile(r"…+|\.{3,}|﹍+|—{2,}")

FOLD = re.compile(r"(.)\1+")            # 相邻同字折叠成 1 个
# 归一化掉的字符。`*` 在里面是因为**引文常被 markdown 加粗**：
#   core/pen.py:21 写的是「**请去昨天晚上帖子里看**」，而这句**在语料里逐字有**
#   （archive/chanlun108/text/lesson-081.txt）—— 旧口径下星号留在 needle 上，
#   一条真引文永远搜不到 ⇒ 报成了 ③。
# ⚠ **改这一行 = 改母体，不只是改分类**：README.md:164 有同一句的**不带星号**版本，
#   两边去掉星号后**合成一个 key** ⇒ 去重后的条数从 152 变 151（不是 152 里换一格）。
#   实测：① 119→120（规范化后 12→13）· ③ 17→16 · 共 152→151 —— 三个 delta 全由这一件事解释。
#   凡是印「共 N 条」的地方，N 都是**这把尺的产物**，不是语料的属性。
# 只加 `*`，**不加 `_`**：中文引文里不会有裸 `*`，但 `_` 可能是真标识符
# （卡名 `c04plus_featureseq` 这种），去它没有独立证据支持（实测贡献 0，且方向不明）。
#
# `↵`（U+21B5，本仓写法里「原文在这一行硬折了行」的标记）2026-10-02 加。
#   它一直待在 `\s` 的**外面**：`\s` 匹配的是真换行，而 `↵` 是一个普通符号。
#   于是语料侧的真换行被 `\s` 抽走、引文侧的 `↵` 原样留着 ⇒ **带折行标记的引文
#   三个严档全落空**，只能掉进 ④「退短词·未定性」—— 而那一档的名字读起来像
#   「这条引文没定性」，其实只说明它带了个折行标记。全仓带 `↵` 的块 1281 个（28 文件）。
#   实测（同一棵树，只改这一个字符）：严档 480→587 ｜ ④ 122→11 ｜ ② 171→168 ｜
#   ③ 178→175 ｜ 共 951→941。
#   ⚠ 又是一个**改这一行 = 改母体**：152 个带 `↵` 的 key 换了名字，其中 10 个
#   **正好撞上一条不带 `↵` 的孪生引文**（同一条原文的两种写法）⇒ 分母 −10。
#   块的出现次数不变（1658 → 1658）⇒ **是合并，不是丢了引文**（10 对列在卡
#   card-c85117e4-7d6 上）。代价：合并时两个站点的课号声称取**并集**，于是
#   「其中一个站点把课号写错了」会被另一个站点盖住 —— 10 对里实测 1 对如此。
PUNCT = re.compile(r"[「」『』“”\"'，。、；：（）()\[\]【】*\s↵]")


def fold(s):
    """只折叠相邻同字，保留标点。"""
    return FOLD.sub(r"\1", s)


def norm(s):
    """最松口径：去标点 + 折叠相邻同字。"""
    return FOLD.sub(r"\1", PUNCT.sub("", s))


def txt_dir():
    return os.path.join(CORPUS, TXT_REL)


def load():
    """按课读 text/ 单文件，不用 全文.txt —— 全量抓取还在写它，读它会有竞态。"""
    TXT = txt_dir()
    if not os.path.isdir(TXT):
        return None                       # 语料不在：交给 main 大声说，不装成空结果
    docs = []
    for f in sorted(os.listdir(TXT)):
        m = re.match(r"lesson-(\d+)\.txt$", f)
        if not m:
            continue
        docs.append((int(m.group(1)),
                     io.open(os.path.join(TXT, f), encoding="utf-8").read()))
    return docs or None


def fingerprint(docs):
    """语料的身份：把每课的 sha256 排好再 hash 一次 ⇒ 一个短指纹。"""
    h = hashlib.sha256()
    total = 0
    for n, body in sorted(docs):
        b = body.encode("utf-8")
        total += len(b)
        h.update(b"lesson-%03d\0" % n)
        h.update(hashlib.sha256(b).hexdigest().encode())
    return h.hexdigest()[:16], total


class Corpus(object):
    """把 108 课拼成一条串 + 课号边界表，一次扫描就能定课号。"""

    def __init__(self, docs, xform):
        self.starts, self.ends, self.nums, parts = [], [], [], []
        pos = 0
        for n, body in docs:
            t = xform(body)
            self.starts.append(pos)
            self.ends.append(pos + len(t))
            self.nums.append(n)
            parts.append(t)
            pos += len(t) + 1                     # +1 = 连接用的换行
        self.blob = "\n".join(parts)

    def where(self, needle):
        """needle 在哪几课出现。"""
        if not needle:
            return []
        out, i = [], self.blob.find(needle)
        while i >= 0:
            j = bisect.bisect_right(self.starts, i) - 1
            if self.nums[j] not in out:
                out.append(self.nums[j])
            i = self.blob.find(needle, i + 1)
        return sorted(out)

    def pos(self, needle):
        """needle 的全部落点（字符下标）——「顺序一致」那一判要的就是它。"""
        if not needle:
            return []
        out, i = [], self.blob.find(needle)
        while i >= 0:
            out.append(i)
            i = self.blob.find(needle, i + 1)
        return out

    def chain_in(self, parts, j):
        """parts 能否按**原顺序**落在第 j 课里（贪心取最小递增落点）。"""
        lo, hi, cur = self.starts[j], self.ends[j], -1
        for p in parts:
            nxt = [x for x in self.pos(p) if lo <= x < hi and x > cur]
            if not nxt:
                return False
            cur = min(nxt)
        return True


def collect():
    """整篇抽「」/『』（允许跨行）：{归一化引文: {...}}"""
    out = {}
    pat = re.compile(r"第\s*(\d{1,3})\s*课")
    qpat = re.compile(r"「([^「」]{6,300}?)」|『([^『』]{6,300}?)』", re.S)
    for root, _d, files in os.walk(REPO):
        if any(x in root for x in SKIP):
            continue
        for f in files:
            if not f.endswith((".py", ".md")):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO)
            text = io.open(p, encoding="utf-8").read()
            lines = text.split("\n")
            for m in qpat.finditer(text):
                q = m.group(1) or m.group(2)
                k = norm(q)
                if len(k) < 6:
                    continue
                ln = text.count("\n", 0, m.start()) + 1
                # 课号取「引文起始那一行」和「它上一行」—— 引文常常写成
                # 「第 81 课正文里：\n 「……」」，课号在上一行。
                window = lines[max(0, ln - 2):ln]
                cites = {int(x.group(1)) for x in pat.finditer("\n".join(window))}
                if not cites:
                    continue
                e = out.setdefault(k, {"quote": q, "claims": set(), "where": [],
                                       "multiline": "\n" in q})
                e["claims"] |= cites
                e["where"].append("%s:%d" % (rel, ln))
                e["multiline"] = e["multiline"] or ("\n" in q)
    return out


TAILP = re.compile(r"[\s。，、；：！？\"'）”’]+$")


def split_ellipsis(q):
    """按省略号切段，返回 (段列表, 类别)。

    判据不是「省略号在句内还是段间」，是 **省略号后面还有没有东西**（口径人：@nova-8980）：

        截尾/掐头（省略号在头或尾，另一侧空无一物）
            ⇒ 不存在"两段被读成一句"的风险，留下的那一整段逐字可核
            ⇒ **无条件合规**，单开一类「截单段」，算严档
        中间挖洞（省略号两侧都有内容）
            ⇒ 必须逐段核：每段都在原文里逐字找到、**顺序一致**、不许拼接

    为什么必须有这几档：合规写法「原文……省略号」里那个省略号**是我们插的**，
    所以整串**按构造就永远逐字搜不到**。仓内先例 cards/c05_center.py:207 就是这个
    形状，而它其实是合规的 —— 旧仪器把一条合规的引文报进了「搜不到」，
    和真编造的引文混在一个箱子里。

    ⚠ 源文自带的省略号是**必须原样保留**的，不是要立规矩的那类。源文里
    **单省略号「…」26 处 / 13 课，双省略号「……」也有 6 处 / 5 课**
    （020/022/028/047×2/075 —— 别信"双省略号 0 处"，那是在**折叠后**语料上量的，
    `fold()` 会把相邻的两个 U+2026 折成一个）。所以**来源不能用单/双判**：
    只能用位置 —— 逐字命中 ⇒ 源文自带，只逐段命中 ⇒ 我们加的。
    这一档不用管源文自带那种：逐字那三档先跑，整串会先命中，轮不到切段。
    """
    body = TAILP.sub("", q)
    if not ELL.search(body):
        return [], "无"          # 没有省略号 ⇒ 这一档不该插手（逐字那三档管它）
    parts = [p.strip() for p in ELL.split(body)]
    parts = [p for p in parts if len(norm(p)) >= 4]
    if not parts:
        return [], "无"
    return parts, ("截单段" if len(parts) == 1 else "多段")


def hunt(corpus, q):
    """返回 (课号列表, 档位)。档位越靠前越严。"""
    for how, needle in (("逐字原样", q),
                        ("折叠叠字后", fold(q)),
                        ("规范化后", norm(q))):
        hits = corpus.where(needle)
        if hits:
            return hits, how
    k = norm(q)
    if len(k) >= 12:
        both = sorted(set(corpus.where(k[:8])) & set(corpus.where(k[-8:])))
        if both:
            return both, "首尾短词"
    if len(k) >= 16:
        m = corpus.where(k[len(k) // 2 - 4:len(k) // 2 + 4])
        if m:
            return m, "中段短词"
    if len(k) >= 10:
        m = corpus.where(k[:7])
        if m:
            return m, "首 7 字"
    return [], "搜不到"


CJK = re.compile(r"[　-〿一-鿿＀-￯]")


def leak_lines(q):
    """引文正文里**带着源码管线记号**的行号（0 起）。空 = 干净。

    这一格治的是"**抽取器抽歪了**"，判据取**正文自己长什么样**，与它搜不搜得到无关：
    `qpat` 用 `[^「」]` 配 `re.S`，一旦跨过字符串字面量边界，抠出来的正文尾部会挂上
    `"…% (…)` 这类源码记号。判据＝**本行最后一个双引号之后没有汉字**
    （正常引文每行结尾是汉字或标点；挂上源码就露出来）。

    实测：151 条里命中 8 条，逐条人工核过 **8/8 真 · 0 假阳**。
    ⚠ 第一版判据是"行尾是 `",` 或 `"`"，**只命中 6** —— 漏了 `cards/c04c_fourcases.py:81`
      和 `cards/c07_level.py:52`，那两条的行尾是 `)`。**判据挂在"行尾形状"上就会漏这种。**
    """
    out = []
    for i, ln in enumerate(q.split("\n")):
        j = ln.rfind('"')
        if j >= 0 and not CJK.search(ln[j + 1:]):
            out.append(i)
    return out


def unpaired():
    """`「` 与 `」` 个数对不上的文件。**这不是统计，是前提断言。**

    `collect()` 的正则用 `[^「」]` 配 `re.S`：只要文件里有一个没闭合的 `「`，
    它就一路吃到下一个 `」`（可以跨过整个字符串字面量）。所以"配对闭合"是判据的前提，
    而**前提今天没有任何一行在守**。实测 76 个文件、**0 个对不上** ——
    正因为今天是 0，才要印出来：让"前提还成立"这件事**每次都有人签字**。
    它不红（只印）：把前提破了的后果接到判据上，是另一件事，不在这一笔里。
    """
    out = []
    for root, _d, files in os.walk(REPO):
        if any(x in root for x in SKIP):
            continue
        for f in files:
            if not f.endswith((".py", ".md")):
                continue
            p = os.path.join(root, f)
            t = io.open(p, encoding="utf-8", errors="replace").read()
            if t.count("「") != t.count("」"):
                out.append((os.path.relpath(p, REPO), t.count("「"), t.count("」")))
    return out


def main():
    docs = load()
    if docs is None:
        print("=" * 78)
        print("语料查不了 —— **什么都没查**，这一条不是「通过」")
        print("=" * 78)
        print("  找的是：%s" % txt_dir())
        print("  本仓不跟踪语料（.gitignore 里有 archive/chanlun108/）。")
        print("  先跑：python3 tools/fetch_chanlun108.py     （源站 https://www.furleader.cn/）")
        print("  或指到已有的那份：QL_CORPUS=<树> python3 tools/verify_quotes.py")
        print()
        print("退出原因: 语料不在 ⇒ exit=2")
        return 2

    fp, nbytes = fingerprint(docs)
    items = collect()
    c_raw = Corpus(docs, lambda s: s)
    c_fold = Corpus(docs, fold)
    c_norm = Corpus(docs, norm)

    print("原文 %d 课 / %.1f MB   语料指纹 sha256:%s"
          % (len(docs), nbytes / 1048576.0, fp))
    print("被审计：%s" % REPO)
    print("仓里**带课号的引文** %d 条（去重），其中**跨行引文** %d 条\n"
          % (len(items), sum(1 for e in items.values() if e["multiline"])))

    # 「一条都没扫到」不等于「都合规」。分母是 0 的时候下面全是 0，退出码也是 0 ——
    # QL_REPO 指错树（指到没有 cards/ 的地方）会和「干净」印得一模一样。
    # 跟语料不在同一条规矩：**什么都没查，不是通过**。
    #
    # 但**基数=0 有两个来源，器不能只报"0"了事**（@iris-64a1 提的）：
    #   (a) 树被指错了（REPO 漂移／工具挪了位置）        ⇒ 人该去看
    #   (b) 这棵树本来就允许是空的（刚建的空仓／只放文档的分支）⇒ 人一句"对，是空的"就完事
    # 器**分不出**这两个（这是它的权限边界，不是它可以含糊的地方）—— 所以两支都 exit=2
    # （2 在本仪器里的含义是"出口封了，人不看不知道"，不是"我什么都没查"），
    # 但**要把它看到的那半个证据说出来**，让人一眼知道该往哪看。
    if not items:
        has_cards = os.path.isdir(os.path.join(REPO, "cards"))
        print("=" * 78)
        print("被审计的树里**一条带课号的引文都没有** —— 这一条不是「通过」")
        print("=" * 78)
        print("  被审计：%s" % REPO)
        print("  分母是 0，下面所有计数都会是 0，退出码也会是 0 —— 和'干净'印得一样。")
        if has_cards:
            print("  这棵树**有 cards/**，却一条带课号的引文都没扫到 ⇒ (b) 形状：")
            print("    要么这棵树枝真是空的，要么抽取器坏了 —— 器分不出，人来看。")
            print("退出原因: 有 cards/ 但扫到 0 条引文 ⇒ exit=2")
        else:
            print("  这棵树**连 cards/ 都没有** ⇒ (a) 形状：大概率是 QL_REPO 指错了树。")
            print("退出原因: 被审计的树不像本仓（没有 cards/）且扫到 0 条 ⇒ exit=2")
        return 2

    def hunt3(q):
        for how, corp in (("逐字原样", c_raw), ("折叠叠字后", c_fold), ("规范化后", c_norm)):
            hits = corp.where(q if how == "逐字原样"
                              else (fold(q) if how == "折叠叠字后" else norm(q)))
            if hits:
                return hits, how
        # 带省略号的引文，按「省略号后面还有没有东西」分两类处理（口径：@nova-8980）
        segs, kind = split_ellipsis(q)
        if segs:
            for tag, corp, xf in (("逐段核（省）", c_raw, lambda s: s),
                                  ("逐段·折叠", c_fold, fold),
                                  ("逐段·规范", c_norm, norm)):
                # 单段 = 截尾/掐头 ⇒ 那段逐字可核就合规
                # 多段 = 中间挖洞 ⇒ 每段对上**且顺序一致**、同课、不许拼接
                # 单段也要给全三档口径，别只认逐字 —— 语料是 OCR 抓的，
                # 105/108 课带相邻同字重复，截出来那一段照样可能需要折叠才中。
                hits = [j for j in range(len(docs)) if corp.chain_in([xf(p) for p in segs], j)]
                if hits:
                    return sorted(corp.nums[j] for j in hits), tag
        return hunt(Corpus(docs, norm), q)

    ok, wrong, gone = [], [], []
    for k, e in sorted(items.items(), key=lambda x: (sorted(x[1]["claims"]), x[0])):
        hits, how = hunt3(e["quote"])
        claims = set(e["claims"])
        if not hits:
            gone.append((e, hits, how))
        elif hits and (set(hits) & claims):
            ok.append((e, hits, how))       # 档位严不严，下面再拆
        else:
            wrong.append((e, hits, how))

    def show(title, rows, note=None):
        print("=" * 78); print("%s   %d 条" % (title, len(rows))); print("=" * 78)
        if note and rows:                   # 空的那一格不必念这段（0 条时它没有对象）
            print(note)
        for e, hits, how in rows:
            print("  「%s」" % e["quote"][:56].replace("\n", "⏎"))
            w = e["where"][0] + (" 等 %d 处" % (len(e["where"]) - 1) if len(e["where"]) > 1 else "")
            print("     仓库标：第 %s 课   %s   [%s]"
                  % (",".join(str(x) for x in sorted(e["claims"])), w, how))
            print("     原文：%s" % (("第 %s 课" % hits) if hits else "——（搜不到）"))
        print()

    by_how = {}
    for e, hits, how in ok:
        by_how.setdefault(how, []).append(e)

    # 分解式与总数**同一个来源**：右边由 STRICT 生成，不是手写名字。
    # 手写的那半不会随档位长 —— 加一档右边就少一项，而它看起来仍像算出来的。
    strict_parts = [(h, len(by_how.get(h, []))) for h in STRICT]
    strict = sum(n for _, n in strict_parts)
    loose = sum(len(by_how.get(h, [])) for h in LOOSE)
    # 不在任何一张清单里的档位：既不在上面的分解里，也不在 ④ 里 —— 会被静默吞掉。
    stray = len(ok) - strict - loose

    print("=" * 78)
    # 这一行原先印的是裸的 `① 课号对上 N 条`，而 N = 严档 + 退短词 —— **它把 ④ 已经算进去了**。
    # 底部汇总又把 ①（只数严档）和 ④ 分开印，于是**同一个字符 `①` 在两处是两个数**：
    #     顶部读 `130 + ②5 + ③16 + ④10 = 161`（多算一遍 ④）｜底部读 151
    # 一份报告两个总数，其中一个是错的 —— 而两个读法都有人会走。
    # 改法是**写清它含了什么**，不是改数：这里一个计数都没动。
    print("① 课号对上 %d 条（= 严档 %d ＋ 第 ④ 格 %d）—— **④ 已经在 %d 里了，别再加一次**；"
          "下面按命中档位拆，严档才算「对上」"
          % (len(ok), strict, loose, len(ok)))
    print("=" * 78)
    for tag, hs in (("严档（可当引文核）", STRICT), ("退短词（**未定性**）", LOOSE)):
        print("  %s" % tag)
        for h in hs:
            n = len(by_how.get(h, []))
            if n:
                print("     %-8s %3d 条" % (h, n))
    print()

    show("② 课号不符（原文有，但不在仓库标的课里）", wrong)
    # ★ ③ 这个标题只说"搜不到"，**没说"是引文"** —— 而末行那句「③ 是真待办」把这层默认说了出来。
    #   @atlas-791f 09:5xZ 把今天 16 条逐条读了它自己那一行的原文（`card-5969a9d9-cb4`）：
    #   **一条编造的引文都没有** —— 2 条是仪器自己的毛病（`c04c_fourcases.py:81` 器抽歪 ·
    #   `core/pen.py:42` 提及，那一行自己写着"原话里没有这句，别加引号当引文用"）、
    #   13 条是仓自己的话（术语 / 给分歧起的名字 / 交叉引用 / 自己造的状态名）、
    #   1 条是转述原文却套了引号（`docs/01_缠论的本质.md:21`）。
    #   ⇒ 处置照本卡 甲2b 的路 C 先例：**报警，不发明分类器**（`use/mention` 没有匹配器能判，
    #     这是本卡第一节的结论）。所以在标题下面把"这格是混装的"说出来，不改任何判据、任何数。
    show("③ 完全搜不到（连退到短词也不中）", gone, note=(
        "  ★ 条数 ≠ 「待核引文数」：这一格是**混装**的 —— 术语、给分歧起的名字、交叉引用、"
        "「提及」（在说某句话，而不是引用它）都会掉进来。\n"
        "    器判不了 use/mention ⇒ 它只保证「这串字在语料里逐字找不到」，"
        "**不保证「这是一条引文」**，更不保证「有人伪造了引文」—— 那是人的判断。"))

    # ④ 原先**只印一个数、不印条目**，而它是唯一在退出码里没有位置的一格
    # ⇒ 一条引文"降进 ④"这件事，报告**答不出来**（人只能自己去调 hunt3）。
    # 实测过这个失败模式不是假想的：抽取器跨行抠引文时会把源码管线一起吃进去
    # （`cards/c04c_fourcases.py:81` 那种 —— 引文被拆在两个 d.text() 里），
    # 而**前半截是真原文 ⇒ 松档照样命中** ⇒ 5 条这类引文全部静默落在 ④，
    # 没有一条去了 ③。**少报的这五条，只有印出来才看得见。**
    show("④ 退短词·**未定性**（不算对上，也不算搜不到）—— 退出码里没有这一格，所以只能靠印",
         [r for r in ok if r[2] in LOOSE])

    # ★ 前提断言：上面所有分类都建立在"`「` 与 `」` 在文件里是配对的"之上
    #   （正则用 `[^「」]` 配 `re.S`，配对一破就吃穿源码）。**今天没有任何一行在守这个前提。**
    _up = unpaired()
    print("前提：「」配对闭合 —— 扫过的每个 .py/.md 里，`「` 与 `」` 个数对不上的：**%d 个**%s"
          % (len(_up), "" if not _up
             else "：" + "、".join("%s（「%d / 」%d）" % x for x in _up)))
    print()

    # ⑤ 治的是"抽取器抽歪了"。★ 它**不是第五格，是一个交叉视图** ——
    #   下面这些条目**同时也在 ①/③/④ 里**（同一条引文被两种方式看见），
    #   所以它**不参与 `共 N 条`**。标题必须把这件事说出来：
    #   今晚已经栽过两次"两处印同一个字符、读的人当成两格"（`①` 一处两名、`合计` 撞桶）。
    _leak = [(e, h, w) for e, h, w in (ok + wrong + gone) if leak_lines(e["quote"])]
    show("⑤ 抽歪了（引文正文里带着源码记号）—— **交叉视图，不是第五格**："
         "下面这些同时也在 ①/③/④ 里，`共 N 条` 不变", _leak)
    print("=" * 78)
    print("① 对上（严档） %d = %s"
          % (strict, " + ".join("%s %d" % (h, n) for h, n in strict_parts if n) or "0"))
    if stray:
        print("   ⚠ 分解式对不上总数：对上 %d 条 · 严档+退短词 %d 条 · 差 %d"
              "（有档位没进 STRICT/LOOSE，会被静默吞掉）"
              % (len(ok), strict + loose, stray))
    print("④ 退短词·**未定性**（不算对上，也不算搜不到） %d" % loose)
    print("② 课号不符 %d      ③ 搜不到 %d" % (len(wrong), len(gone)))
    # 这一行原先印「—— 共 151 条；其中 ①② 是给的、③ 是真待办、④ 要人读」，
    # 而上面四行是**并列印的** ⇒ 读起来像四格相加，可总数只由三格构成（④ 是从 ① 里切出来的）。
    # @nova-8980 就在这几行上真读错过一次（把 120+5+16+10 当成"账加得起来"）——
    # 顶部的警告离这儿 120 行远，救不了这里。**所以写清恒等式，不改任何数。**
    # ★ 而「③ 是真待办」这半句 @nova-8980 09:3xZ 判得对、只是修法不够（见上面 ③ 段头那条注释）：
    #   "真待办" 预设了 ③ 里装的是引文，而它装的是混装的东西。**改标签，不改数、不改判据** ——
    #   `③ 搜不到 %d` 与恒等式、指纹一个都不动。
    print("   —— 共 %d 条 = ① %d ＋ ② %d ＋ ③ %d（**④ %d 在 ① 里，别再加一次**）；"
          "①② 是给的、③ 得人看（器判不出是不是引文）、④ 要人读"
          % (strict + loose + len(wrong) + len(gone),
             strict + loose, len(wrong), len(gone), loose))
    print("   语料指纹 sha256:%s（数变了先看指纹变没变）" % fp)

    bad = len(wrong) + len(gone)
    print("退出原因: 课号不符=%d  搜不到=%d  ⇒ exit=%d" % (len(wrong), len(gone), 1 if bad else 0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
