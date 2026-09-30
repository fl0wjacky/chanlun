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
PUNCT = re.compile(r"[「」『』“”\"'，。、；：（）()\[\]【】\s]")


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

    def show(title, rows):
        print("=" * 78); print("%s   %d 条" % (title, len(rows))); print("=" * 78)
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

    strict = sum(len(by_how.get(h, [])) for h in STRICT)
    loose = sum(len(by_how.get(h, [])) for h in LOOSE)

    print("=" * 78)
    print("① 课号对上 %d 条，**按命中档位拆** —— 严档才算「对上」" % len(ok))
    print("=" * 78)
    for tag, hs in (("严档（可当引文核）", STRICT), ("退短词（**未定性**）", LOOSE)):
        print("  %s" % tag)
        for h in hs:
            n = len(by_how.get(h, []))
            if n:
                print("     %-8s %3d 条" % (h, n))
    print()

    show("② 课号不符（原文有，但不在仓库标的课里）", wrong)
    show("③ 完全搜不到（连退到短词也不中）", gone)

    print("=" * 78)
    print("① 对上（严档） %d = 逐字 %d + 折叠 %d + 规范 %d"
          % (strict, len(by_how.get("逐字原样", [])),
             len(by_how.get("折叠叠字后", [])), len(by_how.get("规范化后", []))))
    print("④ 退短词·**未定性**（不算对上，也不算搜不到） %d" % loose)
    print("② 课号不符 %d      ③ 搜不到 %d" % (len(wrong), len(gone)))
    print("   —— 共 %d 条；其中 ①② 是给的、③ 是真待办、④ 要人读"
          % (strict + loose + len(wrong) + len(gone)))
    print("   语料指纹 sha256:%s（数变了先看指纹变没变）" % fp)

    bad = len(wrong) + len(gone)
    print("退出原因: 课号不符=%d  搜不到=%d  ⇒ exit=%d" % (len(wrong), len(gone), 1 if bad else 0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
