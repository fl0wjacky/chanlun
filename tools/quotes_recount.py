# -*- coding: utf-8 -*-
"""**对账器**，不是判据 —— 把"某句话里的口径"翻成参数，跑出来对上／对不上。

用法（每个旋钮各给一个值，跑法就是这一行）：
    python3 tools/quotes_recount.py --tree 05f3e24 --min-len 6 --face literal \
        --dedup raw --v1ref skip
    python3 tools/quotes_recount.py --tree 05f3e24 --min-len 1 --face whole \
        --dedup norm --v1ref keep --unit gone --ladder norm

★ 头一行原先写 `--json` —— **这支器没有那个旗标**（argparse 里只有下面列的七个），
  照着抄会直接报错。"文档里的写法跑不起来"和"数印出来了分母没跟来"是同族：
  **通道一律报成功，读的人才知道不算。**

它**故意不回答**「哪个才对」。它只回答一件事：**你写下的那句口径，跑出来是几**。
判据在 `tools/quotes_census.py`（那支的三箱与 rc 才是门）；这一支的存在理由是
"口径写成散文，两个人就实现成两条" —— 把散文翻成参数，分歧就变成**可跑的**，
而不是两段各说各话的回忆。

十一个旋钮（就是这一支的全部输入，多一个都没有；`--commit` 还收旧拼法 `--tree`，`-h` 不算）：
★ 这句原来说"八个"而下面列着十个 —— **散文里的计数会烂**，而这一次它烂在了"这支器有几个入口"
  这一格上（`axis_audit` 管得了"有人加了旗标没登记"，**管不了这句话里的数**）。
    --commit  <sha|.>    哪棵树（sha 走 `git archive | tar -x` 到临时目录，跑完删）
                         ★ 这格原来叫 `--tree`，而我传进去的 `05f3e24` 是 **commit**
                           （`git cat-file -t` 说的），tree 是另一个 sha。参数名收得下
                           commit-ish，标签却照参数名印 ⇒ 器在量产含混的标签。
                           现在**印的是解析后的对象**：`commit X → tree Y`。
                           旧拼法 `--tree` 保留可用。
                         ★ **不写这一格 ⇒ exit=4、不出数**（原来是 default="."，见 main）：
                           点 sha = 要跟别人比数；`--commit .` = 明确表示"我知道我在扫工作目录"。
                           两种意图分开写，因为**它们只差一个漏写的参数**。
    --min-len <n>        配对的**长度下限**（按 `norm()` 后的字数算，n=1 表示无下限）
    --face    whole|literal
                         whole   = 整篇正则在源码上扫（引文跨相邻字面量时中间夹 `",\\n"`）
                         literal = 逐字面量扫（拼接的引文被切断 ⇒ 那条判不到）
    --dedup   raw|norm   去重键：配对原文逐字，还是 `verify_quotes.norm(配对)`
    --v1ref   skip|keep  `tools/v1_ref` 跳不跳（其余 SKIP 一律跳：.git/archive/out/__pycache__）
                         ★ 默认已从 skip 翻成 **keep**：卡面那段散文截面是
                           「全仓 *.py 排除 .git/ 与 archive/」，`tools/v1_ref` 两个都不是
                           ⇒ 照散文跑的人该拿到 331；旧的默认会**偷偷再窄一档**、裸跑印 325
                           （实测差 6 处，全在 tools 那格）。默认窄于写下来的口径 = 漏口。
    --expect-corpus <sha256前16位>
                         语料指纹对不上 ⇒ **exit=3、不出数**。
                         ★ 不给它，那行会自报「★ 没核」—— 因为`print(fingerprint)` 只是
                           **印出来**，不是**核过**：换个 QL_CORPUS 指进来，器照样跑、
                           照样印一个 sha256、照样出一张表。**印了 sha256 ≠ 验过语料。**
    --expect-tree <40位 tree sha>
                         **对象**解析出来的树，对不上 ⇒ **exit=6、不出数**。
                         ★ 上面两道门都钉在"你写了什么"上，这道钉在"你指的是哪棵树"上。
                           实测那条刀（@nova-8980 12:5x）：`git tag 05f3e24 335e3a3` 之后，
                           `--commit 05f3e24` **拼法一字不变**，解析出来的树从 `de39cdf7` 变成
                           `45056e42`、数从 331/302 变成 400/360，而门照印「是」。
                         ★ **名字是给人看的，树是给判据用的。**
    --expect-judge <sha256前16位>
                         **判据**（`verify_quotes.py`）的指纹，对不上 ⇒ **exit=5、不出数**。
                         ★ 门原来只核两个输入，但**读数由三个输入决定**：
                           `数 = f(对象, 语料, 判据)`。实测（@nova-8980 12:4x）：
                           判据 `93fbf2ad` ⇒ 331/302「是」；判据换成旧版 `b31431b3` ⇒ **336/307，照样「是」、rc=0**
                           ⇒ 一个**换错了判据**的人会拿到一张自称验收通过、数却不对的表。
                         ★ 尺：sha256（与 `--expect-corpus` 同一把，一个 `sha256sum` 就能独立复算）。
                           同文件另印 git blob 短 sha（团队一直贴的那串），**两把尺各自带名**——不混。
    --expect-flags '<--名 值 …>'
                         **生效旗标串**（`COUNT_AXES` 那六个轴的**解析后**值）逐字对不上
                         ⇒ **exit=8、不出数**。★ 含空格，**要用引号**。
                         ★ 这是第四个自变量：`数 = f(对象, 语料, 判据, ★旗标)`。
                           前三个各有一道门，第四个原来一个都没有 —— 而本卡的验收命令要
                           `--min-len 1`、默认是 6：**漏写一个旗标 = 另一个数**，屏幕上与
                           "照抄的那一跑"逐字节同形（实测：331/302 → 191/182）。
                         ★ 它的词汇表是 `COUNT_AXES` 那一份声明 —— 不是手写的一串格子。
                           （@atlas-791f 13:10 上秤量出来的：手写六格在加了第七个影响数的旗标后
                           **数动而印的那行不动** ⇒ 两个都漏的人串相等 ⇒ 永远绿的门。）
                         ★ 它**进**「验收可用」这个条件（@nova-8980 13:15 的裁决；我原来那处
                           "故意不对称"被打回）：旗标不钉 ⇒ 复现的是**某个**数、不是那张卡上的数 ——
                           而立卡理由就是"光旗标就能挪数"。缺它 ⇒ 印 **`验收可用=否（旗标未钉）`**。
                         ★ 三态，不是两态（@iris-64a1 13:1x）：**"没给"和"给了个空的"不是一件事**。
                           `--expect-flags "$FLAGS"`（变量没展开）⇒ 值**到了器手里** ⇒ 形状那格红（exit=7）；
                           只有真"没给"才是「旗标未钉」。四个 `--expect-*` 一起改（不挑着改）。
    --unit    all|gone   ★ 单位（分母的定义）：
                         all  = **每一个**配对都进分母
                         gone = 只把「在 108 课原文里**找不到**」的配对算进去
    --ladder  norm|norm+ellipsis
                         ★ 阶梯（用哪档判据判"原文里有"）：
                         norm          = 整串规范化后查一次（卡面那套）
                         norm+ellipsis = 再加「逐段核（省）」那一档：含省略号的引文按
                                         `ELL` 切段、逐段规范化、要按原顺序落在同一课里
                                         （`V.split_ellipsis` + `Corpus.chain_in`）

★ `--ladder` 是再后补的，理由和 `--unit` 是同一件事的另一半：**Iris 拍的验收基准是
  「`norm` ＋ 逐段核（省）」= `68 / 50 / 179 / 14`，而在这格接线之前，那个数
  没有任何一条命令印得出来** —— 它只是 `tools/quotes_census.py` 文件头 `:147` 的一行字。
  **一个数只以散文形式存在 = 别人复现不出 = 判据不在公共面上。**
  接线后它是一条命令的输出：

    --unit gone --min-len 1 --face whole --dedup raw --v1ref keep --ladder norm
        ⇒ cards 78 · core 41 · render 16 · tools 182 · config 14 ⇒ **331 处 / 302 条**（卡面）
    --unit gone --min-len 1 --face whole --dedup raw --v1ref keep --ladder norm+ellipsis
        ⇒ cards 68 · core 34 · render 16 · tools 179 · config 14 ⇒ **311 处 / 283 条**
          （core+render = 50 ⇒ 就是验收基准那四格 `68/50/179/14`）

⇒ 报任何一格读数，**阶梯必须连"哪一档"一起报**：同一个旗标换一个值，
  四个桶全动（−10 / −7 / −3 / 0）。

★ `--unit` 是后补的，补的理由值得留着：**少了它，这支器就复现不了 `card-082d9aaa-cbb`
  那四格**。那四格数的**不是**全配对，是"找不到"的那些 —— 我先前把复跑命令写成
  `--min-len 1 --face whole --dedup raw --v1ref keep` 就发出去了，那一行跑出来是
  `577`，不是 `331`。**旋钮表里少了"分母是怎么定义的"这一格，等于没写口径。**

  ★★ **那个 `577` 现在已经成了 `594`** —— 两者都"对"，差的是这一支后来**多印了一行**
  （仓根的 `config.py`，unit=all 下 17 处）：577 + 17 = 594。⇒ **给表加一行，会把所有
  先前发出去的总数**（unit=all 这条轴上的）**静默改掉**，屏幕上没有任何标记说"总数变了"。
  凡把总数贴给别人，就要想到**表还会长**；这与"合计行漏一个它自己刚印过的行"是同一件事的
  两头：**总数和表结构绑着，抄总数不抄表结构，就再也对不上。**

退出 —— ★ **每个码旁边点名它的租客**（@nova-8980 12:5x：一门只有被"**故意让它失败**"的那一跑
证明过才算门；**能印"过"不算本事，能印出"为什么不过"才算**。下面每个码都有一场真跑出来过的红）：

  0  跑完（含"跑完了但**不能当验收读数**"：判据那格会印「否」并说出少了哪一条）
  1  **取不到那棵树** —— git 说 `not a valid object name`（sha 打错一个字符就走这条。实测 `05f3e24aaaa`
     ⇒ fatal + `取不到那棵树`）。★ 这一格原来**没列在这张表里** —— 一个没被列出来的出口码，
     就是一个**没人负责的租客**。（python 自己抛异常也是 1；这一格是"两者共用"，暂时没拆。）
  2  语料不在（**查不了 ≠ 通过**）—— 先跑 `tools/fetch_chanlun108.py`
     ★ 同一个 2 的**第二个租客**：**旗标不认识**（argparse 自己退 2，实测 `--expect-treee`）。
     ⇒ 器在**量之前**就退了 ⇒ 多半是**器拿错版本**（旧树没有这两个新旗标），
       **不是语料没了** —— 屏幕上那行 `unrecognized arguments: --xxx` 才是租客报的名字，
       照着本表去查语料就查错门了。（@atlas-791f 12:43 量到、@bram-9d29 复现后补登记。）
     ★ 同一个 2 的**第三个租客**（@iris-64a1 13:1x 量到）：**值以 `-` 开头 ＋ 空格形式** ——
       `--expect-flags "--min-len"` ⇒ `error: argument --expect-flags: expected one argument`。
       argparse 把那个值当成了**下一个选项**吃掉 ⇒ **器连形状都看不到**（换 `=` 形式
       `--expect-flags="--min-len"` 就交给器 ⇒ 走 **exit=7**）。⇒ 判据：**一道"值形状"的门，
       只能管真的到达函数的那些值** —— 通道可能在门前面就把值吃了，而那声错听着像"你的参数写错了"。
  3  语料指纹对不上（--expect-corpus）—— 换个 `QL_CORPUS` 指进来就会走这条
  4  没点对象（`--commit`/`--tree` 一个都没写）—— 见下面 `--commit` 那格
  5  **判据**指纹对不上（--expect-judge）—— 3 与 5 都"拒绝出数"，但**原因不同**：
     一个是语料换了，一个是**判据换了**（换旧判据 ⇒ 331/302 → 336/307）
  6  **对象解析出来的树**对不上（--expect-tree）—— **名字一样 ≠ 对象一样**
     （`git tag 05f3e24 335e3a3` ⇒ 同一条命令 ⇒ 400/360）
  7  某个 `--expect-*` 给的不是它该有的**形状**（三个是长度、`--expect-flags` 是成对的
     `--名 值`）—— **器还没开始量**。4 和 7 都停在"量之前"，可**原因不同**
     （谁没说清对象／谁把常数打歪了）；"共用一句红"正是今天反复栽的那格 ——
     文字分了，出口码也得跟着分
  8  **生效旗标串**对不上（--expect-flags）—— 第四个自变量（旗标/默认值）。
     ★ 与 3/5/6 分开的理由一样：**这个码只点名"旗标这一维"**。实测差一格就红：
     `--min-len 6` 的期望值 ＋ `--min-len 1` 的实跑 ⇒ 331/302 vs 191/182
  9  **器自己的轴单对不上**（有人加了旗标、`COUNT_AXES`/`OTHER_AXES` 都没登记）——
     租客是**维护者**，不是调用方，所以不许与 4/7 共用（那两个是调用方的错）。
     ★ 它拦在**最前面**（连"没点对象"都排在它后面）：轴单不全是**这一行印出来的东西不可信**，
       那时候再论对象写没写没有意义。★ 它也**只**管"漏登记"这一半 —— 见 `axis_audit`
     ★ 故意红（实测两次）：① 轴单里删掉 `min_len` ⇒ `rc=9`，印出 `有旗标没登记：min_len`；
       ② 加一个 `--bump` 且两个单子都不写 ⇒ 同样 `rc=9`。
       ★ 而**登记错**（真影响数的旗标被登记进 `OTHER_AXES`）它红不了：自查绿、数 331/302→338/309、
       印的那行不动、`--expect-flags` 照旧 rc=0 —— 那一半靠复核，别把边界当覆盖（见 `axis_audit`）。
 10  **离线自测里有门没响**（`--selfcheck-gate`）—— 租客同样是**维护者**，不许与 4/7/9 共用。
     ★ 它是 9 号那扇"永远绿的门"的**另一半**：9 管"**漏登记**"（加了旗标、两个单子都不写），
       10 管"**登记错**"（真影响数的旗标被登记进 `OTHER_AXES`）—— 后者只能靠"换一档看数动没动"，
       而那件事机器判不出来 ⇒ **拿这条命令自己再跑十几遍**。
     ★ 故意红（实测，我跑的）：给副本加一个真影响数的 `--bump` 并登记进 `OTHER_AXES` ⇒
       自测在 ② 那行红 —— `bump 探针=1 ⇒ 合计 335/306（基线 331/302）`。
     ★ 同一格"没测"也走 10（基线跑不出数 / 轴单里的轴没有旗标名）——**不许把"没测"印成"过"**。
     ★ 代价：十几遍真扫（本机 ~16 s）⇒ **离线跑**，不许塞进常规验收（它跑的就是"量之前那几道门"）。

★★ 验收判据：**`grep -q '验收可用=是'`**（输出里那一行单值）。三个条件**必须写成"印了且 = 是"**：

```
验收可用=是    （树=… · 语料 sha256:… 已核 · 判据 sha256:… 已核 · 生效旗标 --min-len 1 --face whole …（已核 --expect-flags））
验收可用=否    ✗ 红（**带名字**：`（旗标未钉）`／`（对象不是 sha · 语料没核 · 判据没核 · 树没核 · 旗标未钉）`，
              下面还会逐条说出"少了哪一条、为什么"）
（没有这一行）      ✗ 红  ← **旧版器就是这一格**：判据若写成"没有 否就算过"，它静默通过
```
  ⇒ ★ 那一行现在还带**生效旗标**（`flagline()`）：语料/判据/树都钉了，**旗标这一维原来一个都没钉**
    —— 而本卡自己的验收命令要 `--min-len 1`，默认却是 6：漏写一个旗标 ⇒ 另一个数，屏幕上与
    "照抄的那一跑"逐字节同形。印的必须是**解析后的生效值**，不是用户写的拼法（也不是 `sys.argv`）。
  ⇒ ★ **印出来只是半扇门**：看得见 ≠ 拦得住。另外半扇是 `--expect-flags`（exit=8），
    而它**进**「验收可用」的条件（缺它就印 `否（旗标未钉）`，@nova-8980 13:15 裁决）。
    ★ 代价（说清，别让它是暗雷）：**所有已经贴出去的老命令都会当场翻「否」** ——
    那声红是准确的（"你引的是新版器、而没钉旗标"），单值 ＋ 说得出的原因，不用重写老卡。
  ⇒ 这门装的是**这个数是什么**，不是"参数写没写"：`--commit .` 是正当用法（exit 照常 0），
    但它不是任何一个对象 ⇒ 换个拼法就能绕过"不写对象"那道 exit=4 的门（@iris-64a1 量到的洞）。
  ⇒ 也**不许借 `★` 当判据**：验收命令**自己**就印 ★（`★ 这一支不判对错…`，在第 15 行）
    ⇒ 按"输出里没有 ★"判会把**正确的那跑**判红。（借别人也在用的字符当接口，本仓栽过。）
"""
import argparse, hashlib, io, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_quotes as V                                   # noqa: E402  口径单一来源

CELLS = ("cards", "core", "render", "tools")
Q = re.compile(r"「([^「」]{1,400}?)」|『([^『』]{1,400}?)』", re.S)


def tree_dir(sha):
    """sha → 临时工作树。`.` 表示就地。"""
    if sha in (".", "", None):
        return None
    d = tempfile.mkdtemp(prefix="recount-")
    p = subprocess.run("git archive %s | tar -x -C %s" % (sha, d),
                       shell=True, cwd=V.ROOT)
    if p.returncode:
        shutil.rmtree(d, ignore_errors=True)
        raise SystemExit("取不到那棵树：%s" % sha)
    return d


def found(q, a):
    """「原文里有」按 `--ladder` 判。

    norm           整串规范化后查一次（卡面那套：78 / 57 / 182 / 14）
    norm+ellipsis  再加「逐段核（省）」那一档 —— 含省略号的引文按 `ELL` 切段，
                   逐段规范化后要求**按原顺序**落在同一课里（`V.Corpus.chain_in`）。
                   ⇒ 这一档把"忠实省略的引用"和"真编造"分开，68 / 50 / 179 / 14。

    ★ 加 `--ladder` 的理由：Iris 拍的验收基准是 `norm + 逐段核（省）`，
      而在这支器加这一格之前，**`68/50/179/14` 没有任何一条命令印得出来** ——
      它只是 `quotes_census.py` 文件头 :147 的一行字。
      「一个数只以散文形式存在」= 别人复现不出 = 判据不在公共面上（见 memory/judgement-not-in-repo.md）。
      接线之后它是一条命令的输出，口径块里那一格就不再靠人手写。
    """
    corpus = a.corpus
    if corpus is None:
        return False                        # unit=all：不判"原文有没有"，这一档不参与
    if corpus.where(V.norm(q)):
        return True
    if a.ladder != "norm+ellipsis":
        return False
    segs, _kind = V.split_ellipsis(q)
    if not segs:
        return False
    parts = [V.norm(p) for p in segs]
    if not all(parts):
        return False
    return any(corpus.chain_in(parts, j) for j in range(len(corpus.nums)))


def pair(m):
    """配对内容。**不许写 `m.group(1) or m.group(2)`** ——
    内层为空时 `group(1) == ''` 是假值，`or` 会掉到 `group(2)`（None）⇒ 成员变成 NoneType。
    当前 `Q` 的 `{1,400}` 下界为 1，够不到这个坑；但 `*` 版本的正则够得到（我今天在探针里真栽过：
    差集一比就 TypeError）。**空值不许冒充成员。**"""
    return m.group(1) if m.group(1) is not None else m.group(2)


def count(base, cell, a):
    n = 0
    keys = set()
    if not os.path.isdir(os.path.join(base, cell)):
        return 0, 0
    corpus = a.corpus                     # None ⇒ unit=all，不建索引（省掉整趟扫描）
    for root, _d, files in os.walk(os.path.join(base, cell)):
        if a.v1ref == "skip" and "v1_ref" in root:
            continue
        if any(("/%s" % s.split("/")[-1]) in root or root.endswith(s)
               for s in V.SKIP if s.split("/")[-1] != "v1_ref" or a.v1ref == "skip"):
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            t = io.open(os.path.join(root, f), encoding="utf-8").read()
            texts = [t] if a.face == "whole" else literal_bodies(t)
            for body in texts:
                for m in Q.finditer(body):
                    q = pair(m)
                    k = V.norm(q)
                    if len(k) < a.min_len:
                        continue
                    if found(q, a):
                        continue                  # 原文里有 ⇒ 不算「找不到」（按 --ladder）
                    n += 1
                    keys.add(q if a.dedup == "raw" else k)
    return n, len(keys)


LIT = re.compile(
    r"(?:[rbfuRBFU]{0,2})(?:"
    r'"""(?:[^"\\]|\\.|"(?!""))*"""'
    r"|'''(?:[^'\\]|\\.|'(?!''))*'''"
    r'|"(?:[^"\\\n]|\\.)*"'
    r"|'(?:[^'\\\n]|\\.)*'" r")")


def literal_bodies(text):
    import ast
    out = []
    for m in LIT.finditer(text):
        try:
            v = ast.literal_eval(m.group(0))
        except Exception:
            continue
        if isinstance(v, str):
            out.append(v)
    return out


def count_config(base, a):
    """仓根的 config.py（不是一级目录 ⇒ `CELLS` 那轮走不到它，但它必须进合计）。"""
    p = os.path.join(base, "config.py")
    if not (os.path.isfile(p) and a.face == "whole"):
        return None
    t = io.open(p, encoding="utf-8").read()
    n, keys = 0, set()
    for m in Q.finditer(t):
        q = pair(m)
        k = V.norm(q)
        if len(k) < a.min_len:
            continue
        if found(q, a):
            continue
        n += 1
        keys.add(q if a.dedup == "raw" else k)
    return n, len(keys)


def tally(base, a):
    """整表跑一遍 ⇒ (rows, tot)。rows = [(名字, 处, 条)]，合计由 rows 现加。

    **抽成函数是为了能跑第二遍**：收尾那行要比"换一档"的差，就得真跑两次。
    """
    rows = []
    for cell in CELLS:
        n, k = count(base, cell, a)
        rows.append((cell, n, k))
    cf = count_config(base, a)
    if cf is not None:
        rows.append(("config.py", cf[0], cf[1]))
    return rows, (sum(r[1] for r in rows), sum(r[2] for r in rows))


def which(sha):
    """参数**真正指的是什么** —— 标签由对象自己说，不许由参数名代说。

    ★ @atlas-791f 12:12 抓的：这参数叫 `--tree`，可我一直传的是 `05f3e24`，
      而 `git cat-file -t 05f3e24` ⇒ **commit**（tree 是另一个 sha）。
      `git archive <commit-ish>` 照样出树，所以它一直"能用" —— 但器把
      `tree=05f3e24` 当量法行印出来，等于**量产一个含混的标签**，
      而卡上那条基准行要从它这儿抄格子。今天那次诊断就是死在"这东西是不是 tree"第①步。

    返回 `(说明文字, 它是不是一个**真正的对象**)`。第二项就是 `验收可用` 那格的左半边
    （@iris-64a1 14:2x 量出来的洞）：`--commit .` 是**正当用法**，它确实该跑、该 exit=0，
    **但它不是任何一个对象** ⇒ 那个数绑的是"你脚下那份工作区的快照"。
    ⇒ **换个拼法就绕过"不写对象"那道门**（`--commit .` 明写出来，照样出数）——
      所以门不能只装在"参数写没写"上，得装在这个数**是什么**上。
    """
    def git(*args):
        p = subprocess.run("git " + " ".join(args), shell=True, cwd=V.ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return p.stdout.decode("utf-8", "replace").strip()

    if sha in (".", "", None):
        # ★ 「就地」是个**不是对象的对象**（@nova-8980 卡上那条验收命令照抄实测出来的）：
        #   同一条命令行，换一个人、换一个工作区、或者工作区脏了，数就变了。
        #   实测：不给对象照抄 ⇒ 430/382；给了 05f3e24 ⇒ 331/302。**两个都"跑得出"。**
        head = git("rev-parse", "--short", "HEAD") or "(没有 HEAD)"
        st = [x for x in git("status", "--porcelain").splitlines() if x.strip()]
        mod = [x for x in st if not x.startswith("??")]
        unt = [x for x in st if x.startswith("??")]
        # ★ 两数分开，且**不许写"已改"**（@atlas-791f 12:2x 的半句对一半错）：
        #   实测未跟踪**本来就**算进这个数（加一个未跟踪 .py，这里 0→1）——
        #   但原来那行写"（N 个文件已改）"，把"未跟踪"也说成"已改"，**标签与内容不符**。
        #   改法不是改判据，是**把两个成分拆开印**。
        return ("就地 %s\n"
                "         ★ 它**不是任何一个 sha 的对象**：工作区 HEAD=%s，与 HEAD 不一致 %d 个"
                "（已跟踪改 %d · **未跟踪 %d**）\n"
                "         ★ 就地走**工作目录**（未跟踪也算分母）；点 sha 走 `git archive`"
                "（只含已跟踪）—— **两条路不是同一把尺**\n"
                "         ⇒ 要跟别人比数，必须点一个对象：`--commit <sha>`"
                % (V.ROOT, head, len(st), len(mod), len(unt)), False)
    kind = git("cat-file", "-t", sha)
    # ★ 两格**合并写**（我跑自己的判据模板时抓到的）：原来 `tree` 那格只回显**传进来的拼法**，
        #   传 `e8944076` 就印 `tree e8944076（…）` —— 40 位的树 sha **一次都不出现**。
        #   指望"对象"那一行当身份的人（我那个模板就是）会**静默解析失败**，
        #   而失败长得和"对象不对"一模一样：**红是对的、原因是错的**，今天栽过好几回的同一格。
        #   ⇒ 统一印 `→ tree <40位>`：这一行的身份由**对象自己**说（`rev-parse`），不由传参的拼法说。
        #     传短 sha、传长 sha、传 tree、传 commit，印出来的都是同一个 40 位。
    # ★ @atlas-791f 12:5x 的便宜加固：**git 本来就会喊**（`warning: refname 'X' is ambiguous`），
    #   是这支器把它吞了（`git archive` 的 stderr 直接漏到终端，捕获 stdout 的检查方看不见）。
    #   ⇒ 不必自己做冲突检测，问一句就够。实测 `git rev-parse --symbolic-full-name <名>`：
    #       普通对象 id / 前缀 ⇒ **空**（rc=0）
    #       被同名 tag 抢走     ⇒ `refs/tags/05f3e24`   ← 实测（`git tag 05f3e24 335e3a3` 之后）
    #   **一句话就能问出"它是名字，还是身份"。**
    ref = git("rev-parse", "--symbolic-full-name", sha)
    warn = ("" if not ref else
            "\n         ★ **这个名字是一个 ref**（%s），不是对象 id ⇒ 解析它 = 信它；"
            "可门要核的是**解析出来的那棵树**\n"
            "         ⇒ 判据请给 `--expect-tree <40位>`。"
            "**名字是给人看的，树是给判据用的。**" % ref)
    if kind in ("commit", "tree"):
        return ("%s %s → tree %s（临时树，跑完删）%s"
                % (kind, sha, git("rev-parse", sha + "^{tree}"), warn), True)
    return ("%s（认不出类型，git cat-file 说 %r）" % (sha, kind), False)


def judge_id():
    """判据的身份 —— **是我真导进来的那个文件**（`V.__file__`），不是"我猜它在哪"。

    ★ 为什么必须钉它：这支器的读数 = **f(对象, 语料, 判据)**。门原来只核前两个
      ⇒ 判据一换，数就变，而门照印「是」、rc=0。两条独立路径量到（@nova-8980 12:4x ·
      @atlas-791f 12:5x）：
        判据换回旧版 `b31431b3`            ⇒ 331/302 → **336/307**，两跑都「是」
        判据里 `norm` 改成恒等、器一字节不动 ⇒ 331/302 → **365/333**
      ⇒ **一个换错了判据的人，会拿到一张自称验收通过、数却不对的表。**

    ★ 只说"这个文件"的 sha256，**不说"判据已钉死"**：那是**闭包断言**。
      今天成立是量出来的（`verify_quotes.py` 只有一行 import，全是标准库 ⇒ 无下游），
      但哪天它自己 import 了第三个文件，那句话就假了 —— 而**假掉的断言不会自己红**。
      所以这里只报事实，闭包由卡上那句"什么时候要重新量"守着。
    """
    p = getattr(V, "__file__", None)
    if not p or not os.path.exists(p):
        return None, None, p
    b = open(p, "rb").read()
    return (hashlib.sha256(b).hexdigest()[:16],
            hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()[:8],
            p)


# ── 数的「轴单」：**唯一一份声明** ──────────────────────────────────────────────
# ★ Why（2026-09-30，@atlas-791f 13:10 复核时给这一行上秤量出来的）：那行原来是 `flagline()`
#   里**手写的六格**，而它印的名字是「生效**旗标**」（一个**类**）。他往副本里加了**第七个**
#   影响数的旗标（`--bump 7`）：合计 331/302 → **338/309**，而那一行**逐字节不变** ——
#   **数动了，印的那行没动。**
#   今天这六格确实覆盖得住（`add_argument` 全列过，影响数的旗标就这六个），所以这**不是缺陷、
#   是边界**；但下一笔 `--expect-flags` 会**继承**它：拿这串当判据词汇表的两个人，若漏了同一个
#   旗标，两条串**比出来相等** ⇒ **一扇永远绿的门**（"一个不可能失败的门不是门"）。
#   ⇒ 修法：六格变成**一份声明**，拼串与自查都从它派生，并让"加了旗标没登记"**会红**。
COUNT_AXES = ("min_len", "face", "dedup", "v1ref", "unit", "ladder")
# ★ 不进分母的旗标也**必须逐个点名** —— 否则自查红不了：登记不全与登记错长得一样，而能红的
#   只有"没登记"那一半（`axis_audit` 的 docstring 写清了它**不**管什么，别把边界当覆盖）。
OTHER_AXES = ("tree", "expect_corpus", "expect_judge", "expect_tree", "expect_flags")
# ★ **模式开关**：它既不进数、也不是"换一档看数动没动"的旋钮（它连量都不量）——
#   所以**单独点名**，不许塞进 `OTHER_AXES`：自测会拿 `OTHER_AXES` 逐项当"探针"跑一遍，
#   混进去 ⇒ 自测自己调自己（`--selfcheck-gate` 递归）。这与对象轴 `--commit` 是**同一类豁免**：
#   **点名豁免，不混进"不许动"那一堆**（照 `card-c9b12e05-1a0` 那条：豁免要按 dest 点名）。
MODE_AXES = ("selfcheck_gate",)
AXIS_FLAG = {"min_len": "--min-len", "face": "--face", "dedup": "--dedup",
             "v1ref": "--v1ref", "unit": "--unit", "ladder": "--ladder",
             "tree": "--commit", "expect_corpus": "--expect-corpus",
             "expect_judge": "--expect-judge", "expect_tree": "--expect-tree",
             "expect_flags": "--expect-flags", "selfcheck_gate": "--selfcheck-gate"}


def axis_audit(ap):
    """自查：**每一个** argparse 动作都必须被登记为"计数轴"或"非计数轴"。

    Why：轴单是手写的，而"这个旗标影响不影响数"**机器判不出来**（argparse 不知道 `--bump`
    会不会进分母）⇒ 这份自查能红的只有**一半**：
      · 管得住：加了旗标、两个单子都没写 ⇒ 红（exit=9）
      · **管不住**：加了个真影响数的旗标、却登记进 `OTHER_AXES` ⇒ 自查绿、而旗标行照旧不变
        ⇒ 那扇"永远绿的门"在**登记错**这一侧的残余，它拦不下。
    两个反证跑都做过（见卡 `card-981814b5-15d`）：① 轴单里删掉 `min_len` ⇒ 红；
    ② 加 `--bump` 并登记进 `OTHER_AXES` ⇒ **绿，而数从 331/302 变 338/309**。
    ⇒ 它不是"测得准"，是"**漏登记会被拦下**"；登记错只能靠复核。
    ★ **登记错**那一半现在有门了（`--selfcheck-gate`，见 `selfcheck_gate`）：把每个 `OTHER_AXES`
      项各塞一个探针值跑一遍，要求**合计逐位不动** —— 真影响数的旗标被登记进 `OTHER_AXES`，
      自测就会红（exit=10）。`axis_audit` 仍然只管道一半，两半各治各的。
    """
    declared = set(COUNT_AXES) | set(OTHER_AXES) | set(MODE_AXES)
    got = set(x.dest for x in ap._actions if x.dest != "help")
    return sorted(got - declared), sorted(declared - got)


def flags_shape_bad(s):
    """`--expect-flags` 的**形状**：成对的 `--名 值`。

    形状不合格 ⇒ 那是**参数写歪了**（exit=7），不是"对不上"（exit=8）—— 这两件事共用一句红，
    今晚已经栽过好几回（"三态共用一个词"）。这里**只查形状**，不查它跟生效值像不像；
    像不像由 8 号那条比。
    """
    toks = s.split()
    if not toks or len(toks) % 2:
        return "应当成对的 `--名 值`，现在拆成 %d 个词：%r" % (len(toks), s)
    for i in range(0, len(toks), 2):
        if not re.fullmatch(r"--[a-z0-9][a-z0-9-]*", toks[i]):
            return "第 %d 个词不是旗标名：%r" % (i + 1, toks[i])
    return None


def flagline(a):
    """把**生效值**拼成一行 —— 不回声用户写的拼法，也不回头去读 `sys.argv`。

    ★ 拼法走**唯一一份声明**（`COUNT_AXES` + `AXIS_FLAG`），不再手写格子 —— 见上面 `COUNT_AXES`
      那段：手写的六格在"加了第七个旗标"时会**静默漏掉**，而这一行的名字比它的算法宽。

    Why（2026-09-30，两次独立撞上）：数的自变量除了对象/语料/判据，**还有默认值本身**
    —— 而默认值是**版本的一部分**，翻过面之后在屏幕上分不开：
      · 同一句"全默认"在这支器的 8 个历史版本上给出 **三个数**（366/334 · 356/325 · 347/316），
        反证行把它拆开了：`9770949f --v1ref skip ⇒ 356/325`，而 `--v1ref keep ⇒ 366/334`
        —— 差的就是那一个默认（`--v1ref` 在某次提交上从 skip 翻成 keep）。
      · 本卡自己的验收命令要 `--min-len 1`，而**默认是 6**：漏写一个旗标 ⇒ 另一个数，
        屏幕上与"照抄的那一跑"逐字节同形。
    ⇒ 判据：器把语料/判据/树都钉了，**旗标这一维一个都没钉**。这一行把它补上。
    ★ 从 `a` 取（解析后的生效值），不从 `sys.argv` 取 —— 后者印的是"用户写了什么"，
      而这里要印的是"**这一跑实际按什么跑的**"。
    """
    return " ".join("%s %s" % (AXIS_FLAG[d], getattr(a, d)) for d in COUNT_AXES)


def build_parser():
    """构造解析器 —— ★ 抽出来是因为**自测要按同一份声明造第二份命令行**
    （枚举每个轴的合法取值、给每个 `OTHER_AXES` 项塞一个'不影响数'的探针值）。
    自测若自己另抄一份旗标清单，那份清单会**跟着漂**（手写的第二份声明 = 一扇永远绿的门）。
    """
    ap = argparse.ArgumentParser()
    # ★ default 从 "." 改成 **None**（@atlas-791f 12:2x 的第三条反例）：
    #   原来不写对象 ⇒ 回落 "." ⇒ 照跑、照印一张表、**exit=0**，格式与一次合法读数一模一样
    #   ⇒ 「抄错也出数」：粘贴时漏掉对象和一次合法读数，屏幕上分不开。
    #   我那三行警告字全对，但只在**打印**这一条通道上说话，退出码那条通道什么都没说。
    #   ⇒ 现在把两种意图**分开写**：点 sha = 要比数；`--commit .` = 明确表示"我知道我在扫工作目录"。
    #     不写 ⇒ **exit=4、不出数**。已发布命令全带对象，所以不破任何一条（逐条核过）。
    ap.add_argument("--commit", "--tree", dest="tree", default=None,
                    help="哪棵 commit（也收 tree/sha）。★ 旧拼法 --tree 保留可用："
                         "卡上已经贴出去的命令不能因为改名跑不动。")
    ap.add_argument("--min-len", type=int, default=6)
    ap.add_argument("--face", choices=("whole", "literal"), default="whole")
    ap.add_argument("--dedup", choices=("raw", "norm"), default="norm")
    # ★ 默认从 skip 翻成 keep（@nova-8980 ① 12:16 抓的）：
    #   卡面写死的截面是「全仓 *.py 排除 .git/ 与 archive/」—— `tools/v1_ref` 两个都不是
    #   ⇒ 按那段散文跑的人应该拿到 331；而默认 skip 会**偷偷再窄一档**，裸跑印 325
    #   （实测：tools 182→176，差 6 处）。**默认值窄于写下来的口径 = ⑬ 扫面自己的漏口**：
    #   分母少了一块，报告照印一个正常的数，屏幕上没有一处说"我少扫了"。
    ap.add_argument("--v1ref", choices=("skip", "keep"), default="keep")
    ap.add_argument("--unit", choices=("all", "gone"), default="all")
    ap.add_argument("--ladder", choices=("norm", "norm+ellipsis"), default="norm")
    # ★ @atlas-791f 12:19 抓的：指纹是**印出来**的，不是**核过**的。
    #   原来只有 `print(fingerprint(docs))`，全支没有一处比对 ⇒ 换个 QL_CORPUS 指进来，
    #   这支器**照样跑、照样印一个 sha256、照样出数**，只有人眼去比才发现。
    #   ⇒ 有门才叫验过：对不上 exit=3（2 已经给了"语料不在"）。
    ap.add_argument("--expect-corpus", default=None, metavar="<sha256前16位>",
                    help="语料指纹对不上就 exit=3。不给 ⇒ 那行会自报「★ 没核」。")
    # ★ 第二个洞（@nova-8980 12:4x 量到、@atlas-791f 12:5x 独立变异复现）：
    #   门核的是「对象 + 语料」，可这支器的数**由三个输入决定** —— 判据是第三个。
    #   ⇒ 照 --expect-corpus 那把尺再钉一次（**不另发明概念**）：同一个模样、同一个出口形态。
    ap.add_argument("--expect-judge", default=None, metavar="<sha256前16位>",
                    help="判据 verify_quotes.py 的指纹对不上就 exit=5。"
                         "不给 ⇒ 那行会自报「★ 没核」。")
    # ★ 第三个洞（@nova-8980 12:5x）：`git tag 05f3e24 335e3a3` ⇒ 拼法不变、对象换了、门照印「是」。
    #   ⇒ 前三道门都钉在「你写了什么」上，这一道钉在「你指的是哪棵树」上。
    ap.add_argument("--expect-tree", default=None, metavar="<40位 tree sha>",
                    help="对象解析出来的树 sha 对不上就 exit=6。"
                         "不给 ⇒ 判据那格会说出「树没核」。")
    # ★ 第四个洞（@nova-8980 那句"引它必须连剥法一起引"的延长线；@atlas-791f 13:10 指出：
    #   这一格**必须先修轴单**，否则它是**一扇永远绿的门**——两个人都漏了同一个旗标，
    #   串比出来相等）。⇒ 上面 `COUNT_AXES` 先落地，这里才接线。
    #   `数 = f(对象, 语料, 判据, ★旗标)` —— 前三个各有一道门，第四个原来一个都没有。
    ap.add_argument("--expect-flags", default=None, metavar="'<--名 值 …>'",
                    help="生效旗标串（解析后的值）逐字对不上就 exit=8。"
                         "不给 ⇒ 那一格自报「★ 没核」。★ 它含空格，**要用引号**。")
    # ★ **离线自测**（`card-c9b12e05-1a0`）：不进正常跑法。
    #   它把**同一条命令行**再跑十几遍，每次只翻一格，看门/数按不按登记单说的那样动。
    #   要跑十几遍真扫（每次 ~1s）⇒ 别塞进常规验收，也别塞进 CI 的每次跑。
    ap.add_argument("--selfcheck-gate", action="store_true",
                    help="离线自测（不进正常跑法）：① 反向控制四格必须**拒绝出数**；"
                         "② 每个 `OTHER_AXES` 项塞探针值 ⇒ **合计必须逐位不动**（登记错会红）；"
                         "③ 每个计数轴换一档 ⇒ **印出的旗标行必须动**（数动没动只当提示）。"
                         "有一道门没响 ⇒ exit=10。")
    return ap


# ── 离线自测（`--selfcheck-gate`）：把**同一条命令行**再跑十几遍，每次只翻一格 ─────────────
def _strip_flag(argv, flag, takes_value=True):
    """从命令行里摘掉一个旗标 —— `--flag 值` 与 `--flag=值` 两种拼法都认。

    ★ `takes_value=False` 是给**不取值**的旗标用的（`action="store_true"`，如 `--selfcheck-gate`）。
      第一版一律按"它一定带一个值"摘，于是**紧跟其后的那个词被一起吃掉**：
      `… --selfcheck-gate --unit all` ⇒ 基线成了 `… all`（`all` 成了野位置参数）⇒ 基线 rc=2
      ⇒ 整支自测 exit=10。**同一组生效值、只把 `--unit` 往前挪一位，判词就翻面**
      （@nova-8980 那条 A/E 判据当场逮住的；这也正是本卡的「身份不是写法」——
      helper 里对**旗标形状**的假设，和我从 argv 里找默认值是同一类错）。
    """
    out, i = [], 0
    while i < len(argv):
        t = argv[i]
        if t == flag:
            i += 2 if takes_value else 1
            continue
        if t.startswith(flag + "="):
            i += 1
            continue
        out.append(t)
        i += 1
    return out


def _alt_value(act, cur):
    """给一个轴挑一个**不同的合法值**（有 `choices` 就从中挑，整数就 +1）。

    ★ 不另手写一份"第二取值表"：那种表会跟着漂，而漂掉的清单本身就是一扇永远绿的门
      （`COUNT_AXES` 那一段已经栽过一次：手写的六格 vs 加进来的第七个旗标）。
      挑不出来 ⇒ 返回 None，由调用方印成「**没测**」（不许当通过）。
    """
    if act.choices:
        for c in act.choices:
            if str(c) != str(cur):
                return str(c)
        return None
    if act.type is int:
        return str((cur if isinstance(cur, int) else 0) + 1)
    return None


# 轴 dest → `量法` 那一行里的字段名（两套名字，**必须对得上**，否则"只动一根"判不出来）。
MEASURE_KEY = {"tree": "commit", "min_len": "min-len(norm后)", "face": "face",
               "dedup": "dedup", "v1ref": "v1_ref", "unit": "unit", "ladder": "ladder"}


def _coords(out):
    """那一跑**器自己印的坐标行**：量法 / 对象 / 语料 / 判据 四行（注解切掉）。

    ★ 为什么不用 `验收可用=` 那一行：它在「否」的分支里**根本不印坐标**（只印"为什么否"），
      而自测每一跑都可能是否 ⇒ 拿它当坐标 ＝ 有的跑比、有的跑不比（"没测"混进"相同"）。
      这四行**两个分支都印**，所以每一跑都可比。
    ★ 四行抽不齐 ⇒ None。**"没印"与"相同"是两件事** —— 不许让抽不到当成抽到一样的。
    ★ 注解（`（已核：== --expect-corpus）` / `（★ **没核**：…）`）**先切掉**：那是"核过没核过"，
      不是坐标；② 那格塞进去的正是期望值，注解必然会变。
    """
    got = []
    for p in (r"^量法\s+(.+)$", r"^对象\s+(.+)$", r"^语料\s+(.+?)\s*（", r"^判据\s+(.+?)\s*（"):
        m = re.search(p, out, re.M)
        if not m:
            return None
        got.append(re.sub(r"\s+", " ", m.group(1)).strip())
    return got


def _fields(line):
    """`量法` 那行按 ` · ` 拆成 `字段名 → 值`（切开**第一个** `=`，值里还有 `=` 也不怕）。

    行首那个 `口径参数：commit=…` 要把前缀削掉，否则字段名成了 `口径参数：commit`
    —— 而 `MEASURE_KEY` 里写的是 `commit`，两套名字对不上 = 这条检查静默失效。
    """
    out = {}
    for t in line.split(" · "):
        if "=" not in t:
            continue
        k, v = t.split("=", 1)
        out[k.strip().split("：")[-1]] = v.strip()
    return out


def _coord_diff(c0, c1):
    """两跑坐标的差 —— 返回**差在哪几处**（单位：字段名）。抽不齐 ⇒ None。

    · 量法行：逐字段比（单位 = 轴）
    · 对象 / 语料 / 判据 三行：**整行逐字比**（每一行就是一整个坐标）
    """
    if not c0 or not c1 or len(c0) != len(c1):
        return None                       # 「没印」/「行数不等」⇒ **判不了**，不是「相同」
    diffs = []
    for i, name in ((1, "对象"), (2, "语料"), (3, "判据")):
        if c0[i] != c1[i]:
            diffs.append(name)
    f0, f1 = _fields(c0[0]), _fields(c1[0])
    for k in sorted(set(f0) | set(f1)):
        if f0.get(k) != f1.get(k):
            diffs.append(k)
    return diffs


def _alt_base(argv, cur):
    """★ 参数 `cur` 是**解析出来的生效值**，不是从 argv 里找的 —— @nova-8980 当场抓的那条：
    旗标**没写**时它取默认值，而从 argv 里找只会找到 `None` ⇒ 我第一版把它当成 `all`
    ⇒ 当默认本来就是 `all` 时，"另一基点"和基点**一模一样** ⇒ 白跑两遍还照旧判：
    `--commit 05f3e24 --selfcheck-gate`（默认跑法）下 `--ladder` 那格被**假红**。
    ⇒ 生效值只能从 parser 那儿拿（这正是本卡那条：**身份不是写法**）。
    """
    """给"这根计数轴是不是**哑的**"另找一个基点 —— 只动 `--unit` 一档（`all` ↔ `gone`）。

    ★ **只试一个，且它是从调用方那条命令里派生的**（把它自己的 `--unit` 翻到另一个合法值）：
      · 不是一张写死的候选表（那张表会跟着漂），
      · **更不是"搜到动为止"** —— 那是**寻绿**：一根真哑的轴只要在某个稀奇基点上凑出"动"
        就会被判成"被掩住"，而寻绿是假绿的上游（@iris-64a1 的落前一问）。
      ⇒ "换基点会动"这半句的证据力来自它**是一次两点受控比较**：那两跑只差这一个轴的值
        ⇒ 数动了 ⇒ 这个轴真的进分母（哑轴在任何基点都动不了）。

    ★ 为什么需要它（实测，不是推的）：同一根轴 `--min-len 1→2`
      在 `--unit gone` 面上 **恒等**（331/302 → 331/302），
      在 `--unit all`  面上 **动**（594/520 → 566/500）
      ⇒ 计数轴可以在**某个基点上合法恒等**（@atlas-791f 在 card-c9b12e05 评论 1 上量的
      `--unit all` 面两档 `--ladder` 恒等 594/520 是同一个形状）⇒ 拿"这个基点没动"判死
      会造**假红**；而"**任何**基点都不动"是真缺陷（登记成计数轴、却接不上分母）。
      ⇒ 只给"没动"的那几根多跑两遍，把这两种分开（@iris-64a1 点的那格）。
    """
    return _strip_flag(argv, "--unit") + ["--unit", "gone" if cur != "gone" else "all"]


def _diff_text(dif):
    """坐标差的**脸** —— 三种情况必须印成**三张不同的脸**（@iris-64a1 的收口）：

    · `判不了`：坐标行抽不齐 / 两侧行数不等 / 探针那一跑没印出来
    · `逐字相同`：差 0 处
    · `差 N 处：…`：真差了几处、差在哪几处

    ★ 「判不了」和「差两处」要的修法**正相反**（一个是探针/抽行坏了，一个是真动了两根轴）
      —— 共用一张脸，读的人就分不出该修哪边。这就是今晚那句「**没给**」与「**给了个空的**」
      不许共用一张脸，套在这条检查自己身上。
    """
    if dif is None:
        return "**判不了：坐标行抽不齐 / 两侧行数不等 / 那一跑没印出来**"
    if not dif:
        return "逐字相同"
    return "**差 %d 处：%s**" % (len(dif), "/".join(dif))


def _verdict(diff, want_keys):
    """这条检查的判据本身 —— **抽出来是为了能被喂一次"故意差两处"去验它会不会红**。

    `diff is None`（有一跑没印坐标行）⇒ **不通过**：判不出来 ≠ 判过了。
    """
    return diff is not None and sorted(diff) == sorted(want_keys)


def _run_once(argv):
    """按同一条命令跑一遍**子进程** —— `(rc, 合计, 生效旗标行, 坐标行)`，没印出来的是 None。

    走子进程不是图省事：这几道门都拦在"量之前"，只有真跑一遍才算数（同进程复用状态
    会把"没量"演成"量过"）。`合计` 抽不到 ⇒ None，**"0 行"必须有别于"0 处"**。
    """
    r = subprocess.run([sys.executable, __file__] + argv, capture_output=True, text=True)
    m = re.search(r"^\s*合计\s+(\d+) 处 /\s+(\d+) 条", r.stdout, re.M)
    f = re.search(r"生效旗标\s+(--[^\n（]*)", r.stdout)
    return (r.returncode,
            "%s/%s" % (m.group(1), m.group(2)) if m else None,
            f.group(1).strip() if f else None,
            _coords(r.stdout))


def selfcheck_gate(a, argv):
    """离线自测：**这一卡要治的那扇永远绿的门，在这里被做成会红的**（不进正常跑法）。

    Why：`axis_audit`（exit=9）只拦得住"**漏登记**"（加了旗标、两个单子都没写）。"**登记错**"
    （真影响数的旗标被登记进 `OTHER_AXES`）它红不了 —— 实测 `--bump 7` 那种：自查绿、
    `合计` 331/302 → 338/309、而印出来的旗标行**逐字节不动**、`--expect-flags` 照旧 rc=0。
    这一格的判据只能是"**换一档看数动没动**"，而这件事机器判不出来 ⇒ **拿命令自己跑**。

    三块，**判据各不相同**（这一格治的正是"把三种不同的东西用一句绿盖住"）：

      ① 反向控制（**门**）：语料/判据/树/旗标 四格各把**正确值**改坏一位 ⇒
         必须**拒绝出数**（`合计` 抽不到）且 rc 各自是 3/5/6/8。
      ② 登记错（**门**）：每个 `OTHER_AXES` 项塞一个探针值 ⇒ `合计` 必须**逐位不动**。
         ★ 对象轴 `tree`（`--commit`）**点名豁免**：换对象 = 换一次测量，不是旋钮
           —— 豁免要按 dest 点名，不许混进"不许动"那一堆（`--tree` 是同一个参数的另一拼法）。
      ③ 计数轴（**门 + 提示**）：每项换一档 ⇒ **印出的旗标行必须动** **且** 坐标**只许差
         这一根**（门）；`合计` 动没动只印成**提示**、**不判红** —— 真轴在某个合法基点上
         **可以恒等**（实测 `--unit all` 面上两档 `--ladder` 恒等），判红会制造**假红**，
         而一次假红足以让人把整扇门关掉（与"永远绿"同害，方向相反）。
      ④ 自证（**门**）：把两根轴一次碰掉 ⇒ ③ 那条"只许差一处"的判据**必须说不通过**。
         不喂这一口，"只许差一处"本身就是一条**不能失败的检查**（@iris-64a1：刚落这条修法
         的人最容易在新那一层复犯旧病），而它长得和成功一模一样。

    ★ ②③ 比的**不是"动了没有"，是"差在哪几处"**（@iris-64a1 抓的）：只核前者的话，两跑
      差两根轴也是"动了"，而那时差的数**归因不了** —— 失败与成功同签名。
      比的两侧**必须是器自己印的坐标行**（`量法`/`对象`/`语料`/`判据` 四行，
      `_coords()` 从那一跑的 stdout 里抽），不许拿调用方拼的串 —— 拼的两样天然一致。
    ★ 三种结果**三张脸**（`_diff_text`）：`判不了`（抽不齐/行数不等/那跑没印出来）·
      `逐字相同` · `差 N 处：…`。前两者要的修法正相反，不许共用一张脸。
    ★ 代价：十几遍真扫（每遍 ~1s）⇒ **离线跑**，别塞进常规验收。
    ★ 期望值从哪儿来：①里那四个"正确值"是**器自己当场算的**（`V.fingerprint` / `judge_id()` /
      对象自己说的树 / `flagline`）。这里**不是**"抄自己印的那一行"那个病：抄自己印的值当
      **期望值**会让门变回音；而这里是**反向控制** —— 把正确值改坏，门**必须响**，
      期望值对不对不影响这一格的结论（它要证明的是门会响，不是值有多对）。
    """
    # ★ 轴单里点名了、却**没给它旗标名**（`AXIS_FLAG` 少一格）⇒ 这个轴**名字都印不出来**：
    #   `flagline()` 那行会漏掉它，而自测也没法给它塞探针 ⇒ 记成**没测**（红），不许静默跳过。
    #   （`axis_audit` 只管"argparse 里的动作有没有被登记"，不管"登记了的有没有旗标名"。）
    missing_name = [d for d in COUNT_AXES + OTHER_AXES if d not in AXIS_FLAG]
    if missing_name:
        print("★ 轴单里有 %s，但 `AXIS_FLAG` 里没有它的旗标名 ⇒ 这个轴连**名字都印不出来**"
              % ", ".join(missing_name))
        print("  ⇒ 自测**没测**它（exit=10）。先补 `AXIS_FLAG`。")
        return 10

    ap2 = build_parser()
    acts = {x.dest: x for x in ap2._actions if x.dest != "help"}
    base = _strip_flag(argv, "--selfcheck-gate", takes_value=False)
    # 基线 = **调用方那条命令**，只把**期望值**摘掉（那是自测自己要塞的东西）。
    # ★★ 两个都不许摘，各有一次实测教训：
    #   · **对象不许摘**（`tree`）：它是**测量对象**不是期望值 —— 我第一版把 `OTHER_AXES` 整串
    #     都摘了，基线成了「没点对象」（rc=4）⇒ 整场自测退化成"没测"。
    #   · **计数轴不许摘**：摘了 ⇒ 基线跑的是**默认值**，而 ② 那格塞进去的期望值是从**调用方
    #     那条命令**算出来的 ⇒ 拿 A 的期望值去比 B 的实跑，`--expect-flags` 假红（实测 rc=8）；
    #     ③ 那格同理：把 `--dedup raw` 换成默认的 `norm`，旗标行"没动"也是假的。
    #   ⇒ 这条正好是本卡自己的规矩：**豁免要按 dest 点名**（对象轴），**基线要跟被测对象同一条命令**。
    for d in tuple(x for x in OTHER_AXES if x != "tree"):
        base = _strip_flag(base, AXIS_FLAG[d])
    rc0, tot0, fl0, cd0 = _run_once(base)
    print("自测    对象=%s · 基线 rc=%d · 合计=%s · 旗标行=%s"
          % (a.tree, rc0, tot0, fl0))
    print("   基线坐标行（2/3 那两格都拿它当参照，**逐字重述**）：")
    for x in (cd0 if cd0 is not None else ["**没印出来**（⇒ 2/3 判不了，走「没测」）"]):
        print("     %s" % x)
    if rc0 != 0 or not tot0 or cd0 is None:
        print("★ 基线自己都跑不出数（或坐标行印不出来）⇒ **自测没测**（exit=10）。"
              "先把这条命令跑通再来 ——")
        print("  「没测」与「测了没过」不许共用一句话（今晚反复栽的那格）。")
        return 10

    docs = V.load()
    obj_text, _ = which(a.tree)
    mt = re.search(r"→ tree ([0-9a-f]{40})", obj_text)
    good = {"expect_corpus": (V.fingerprint(docs)[0] if docs else None),
            "expect_judge": judge_id()[0],
            "expect_tree": mt.group(1) if mt else None,
            "expect_flags": flagline(a)}
    want = {"expect_corpus": 3, "expect_judge": 5, "expect_tree": 6, "expect_flags": 8}
    gates = red = 0

    print("\n① 反向控制（门：必须**拒绝出数**，`合计` 一行都不许有）")
    for d in ("expect_corpus", "expect_judge", "expect_tree", "expect_flags"):
        g = good[d]
        if not g:
            print("   %-15s ★ 挑不出「正确值」⇒ **没测**（记一笔）" % d)
            gates += 1
            red += 1
            continue
        if d == "expect_flags":
            t = g.split()
            t[1] = "0"
            badv = " ".join(t)
        else:
            badv = g[:-1] + ("0" if g[-1] != "0" else "1")
        rc, tot, _, _ = _run_once(base + [AXIS_FLAG[d], badv])
        ok = (rc == want[d] and tot is None)
        gates += 1
        red += 0 if ok else 1
        # ★ 证据要能看出**差在哪一位**：印两端会把"改坏了一位"藏起来（`--expect-flags` 那格改的是
        #   第一个词、`sha` 那几格改的是末位 —— 一律印头或一律印尾都必然有一格看不见）。
        k = next((i for i in range(min(len(g), len(badv))) if g[i] != badv[i]), 0)
        print("   %-15s 好值 …%s… 改坏成 …%s… ⇒ rc=%d（要 %d）· 合计 %s ⇒ %s"
              % (d, g[max(0, k - 4):k + 8], badv[max(0, k - 4):k + 8],
                 rc, want[d], tot or "**没有**", "✓" if ok else "✗ **门没响**"))

    print("\n② 登记错（门：非计数轴塞探针 ⇒ `合计` **逐位不动** 且 **坐标行逐字重述**）")
    print("   ★ 点名豁免：`tree`（--commit）—— 换对象 = 换一次测量，不是旋钮")
    print("   ★ 坐标行 = 器自己印的 量法/对象/语料/判据 四行；**差哪一处都要点名**"
          "（只核「动了没有」的话，「动两根」和「动一根」同签名 —— @iris-64a1 抓的）")
    for d in OTHER_AXES:
        if d == "tree":
            continue
        act = acts.get(d)
        v = good.get(d)
        if v is None and act is not None:
            v = _alt_value(act, getattr(a, d, None))
        if v is None:
            print("   %-15s ★ 挑不出探针值 ⇒ **没测**（记一笔）" % d)
            gates += 1
            red += 1
            continue
        rc, tot, _, cd = _run_once(base + [AXIS_FLAG[d], v])
        dif = _coord_diff(cd0, cd)
        ok = (rc == 0 and tot == tot0 and _verdict(dif, []))
        gates += 1
        red += 0 if ok else 1
        print("   %-15s 探针=%s ⇒ rc=%d · 合计 %s（基线 %s）· 坐标 %s ⇒ %s"
              % (d, v[:20], rc, tot or "**没有**", tot0, _diff_text(dif),
                 "✓" if ok else "✗ **%s**" % (
                     "数动了 ⇒ 登记错" if tot != tot0
                     else ("判不了 ⇒ 先修抽行/探针（**没测**）" if dif is None
                           else "坐标动了 ⇒ 这个探针不止碰一根轴"))))

    print("\n③ 计数轴（门：印出的旗标行必须动 · 提示：数动没动**不判红**）")
    ax_moved = ax_same = 0
    for d in COUNT_AXES:
        act = acts.get(d)
        v = _alt_value(act, getattr(a, d, None)) if act is not None else None
        if v is None:
            print("   %-15s ★ 挑不出第二值 ⇒ **没测**（记一笔）" % d)
            gates += 1
            red += 1
            continue
        rc, tot, fl, cd = _run_once(base + [AXIS_FLAG[d], v])
        dif = _coord_diff(cd0, cd)
        line_ok = (rc == 0 and fl is not None and fl != fl0)
        # ★ 门 = "旗标行必须动" **且** "坐标**只许差这一根**"：只核前者的话，两跑差两根轴
        #   也会"动" —— 那时差的数**归因不了**，而它照样绿（@iris-64a1 那句"失败与成功同签名"）。
        one_ok = _verdict(dif, [MEASURE_KEY[d]])
        moved = tot != tot0
        ax_moved += 1 if moved else 0
        ax_same += 0 if moved else 1
        # ★ "这个基点恒等"**不等于**"这根轴是哑的"：换一个基点再翻同一根轴，把两支分开
        #   （活轴被基点掩住 ⇒ 提示；任何基点都不动 ⇒ 红，脸=「接上了但数没跟」）。
        alive, why_num = None, ""
        if not moved and line_ok and one_ok:
            alt = _alt_base(base, getattr(a, "unit", None) or "all")
            rcA, totA, flA, _ = _run_once(alt)
            rcB, totB, _, _ = _run_once(alt + [AXIS_FLAG[d], v])
            if rcA == 0 and rcB == 0 and totA and totB:
                alive = (totA != totB)
                why_num = "另一基点**试了 1 个**（调用方命令只翻 --unit，不搜）: %s ⇒ %s → %s ⇒ %s" % (
                    flA or "旗标行没印", totA, totB,
                    "动（这根轴是活的，被这个基点掩住）" if alive else "**也不动**")
            else:
                why_num = "另一基点跑不出数 ⇒ **没测**"
        gates += 1
        num_ok = moved or (alive is True)
        red += 0 if (line_ok and one_ok and num_ok) else 1
        # ★ ✗ 也得**分脸**：**没做成的比较**不许印成**做成了的比较**
        #   （@atlas-791f 那条：另一基点没测时，✗ 列原先照样印"这根轴是哑的"——
        #    那是把"我没量"说成"对象如此"，两句话要的下一步正相反）。
        if not line_ok:
            tail = "印的那行没跟着动"
        elif dif is None:
            tail = "判不了 ⇒ 先修抽行/探针（**没测**）"
        elif not one_ok:
            tail = "坐标不止动一根 ⇒ 这跑的数归因不了"
        elif moved or alive is True:
            tail = "（不该到这）"
        elif alive is False:
            tail = "接上了但数没跟（**这两个基点**都不动 —— 两点比较，**不蕴含**「任何基点都不动」）"
        else:
            tail = "**判不了：另一基点没能比较 ⇒ 这格「没测」**（不许当绿，也不许印成「哑轴」）"
        print("   %-15s →%-14s rc=%d · 合计 %s ⇒ 数%s · 旗标行%s · 坐标差 %s ⇒ %s"
              % (d, v, rc, tot or "**没有**",
                 "动" if moved else ("**恒等**" + ("（%s）" % why_num if why_num else "（提示，不判红）")),
                 "动" if line_ok else "**没动**",
                 ("只 %s（其余逐字同）" % MEASURE_KEY[d]) if one_ok else _diff_text(dif),
                 "✓" if (line_ok and one_ok and num_ok) else "✗ **%s**" % tail))

    # ★ ④ 这条门**自己也得能被喂红**：把两根轴一次碰掉 ⇒ 上面那条判据**必须**说"不通过"。
    #   不喂这一口的话，"只许差一处"就成了一条**不能失败的检查** —— 而它长得和成功一模一样
    #   （@iris-64a1：刚落这条修法的人，最容易在新那一层复犯旧病）。
    print("\n④ 自证（门：这条「只许差一处」的判据，喂它一次故意差两处 ⇒ 必须红）")
    pair = [(d, _alt_value(acts.get(d), getattr(a, d, None))) for d in COUNT_AXES[:2]]
    pair = [(d, v) for d, v in pair if v is not None]
    if len(pair) < 2:
        print("   ★ 挑不出两根轴 ⇒ **没测**（记一笔）")
        gates += 1
        red += 1
    else:
        argv2 = list(base)
        for d, v in pair:
            argv2 += [AXIS_FLAG[d], v]
        rc, tot, _, cd = _run_once(argv2)
        dif = _coord_diff(cd0, cd)
        two = sorted(MEASURE_KEY[d] for d, _ in pair)
        # 这里要的是"判据**拒绝**"：差两处却按"只许差一处"判 ⇒ 必须 False。
        refused = not _verdict(dif, [two[0]])
        gates += 1
        red += 0 if refused else 1
        print("   一次碰两根（%s）⇒ 坐标 %s ⇒ 按「只许差一处」判 ⇒ %s"
              % ("+".join("%s→%s" % (d, v) for d, v in pair), _diff_text(dif),
                 "**不通过**（判据会红，✓）" if refused else "**通过**（✗ 这条判据是 no-op！）"))

    print("\n★ 自测结论：门 %d 道，红了 %d 道 ⇒ %s"
          % (gates, red, "全响（exit=0）" if not red else "**有门没响（exit=10）**"))
    print("   （提示不算门：③ 只算「旗标行必须动」那 %d 道；"
          "计数轴上「数动」的 %d 道、恒等的 %d 道都只是印出来给人看）"
          % (len(COUNT_AXES), ax_moved, ax_same))
    return 0 if not red else 10


def main():
    ap = build_parser()
    a = ap.parse_args()

    # ★ 器**自己**的自查先跑（exit=9）：轴单不全 ⇒ 这一行印出来的东西就不可信，
    #   所以它拦在**最前面**，连"没点对象"都排它后面。(「谁的错」：这一格是维护者的错。)
    unknown, missing = axis_audit(ap)
    if unknown or missing:
        print("★ 器自己的**轴单**对不上 ⇒ 拒绝出数（exit=9）。这一格**不是调用方的错**：")
        print("    有旗标没登记：%s" % (", ".join(unknown) or "（无）"))
        print("    登记了没旗标：%s" % (", ".join(missing) or "（无）"))
        print("  ★ 为什么要拦在量之前：「生效旗标 …」那一行是从 `COUNT_AXES` 拼出来的，"
              "漏登记一个影响数的旗标 ⇒ **数会动、印的那行不动**；")
        print("    而 `--expect-flags` 拿它当判据词汇表 ⇒ 两个都漏的人串相等 ⇒ 一扇永远绿的门。")
        print("  ★ 修法：在 `COUNT_AXES`（进分母）或 `OTHER_AXES`（不进）里点名它 —— "
              "**两个单子都不写，就是这一格。**")
        return 9

    if a.tree is None:
        print("★ 没点对象 ⇒ **拒绝出数**（exit=4）。这支器量的是「某个提交的树」，")
        print("  不是「此刻谁的工作目录」—— 而这两件事**只差一个漏写的参数**：")
        print()
        print("    --commit <sha|tree>   要跟别人比数 ⇒ 用这个")
        print("    --commit .            确实要扫**当前工作目录**（含未跟踪）⇒ 也请明确写出来")
        print()
        print("  ★ 不写也能跑 = 「抄错也出数」：粘贴时漏掉对象，和一次合法读数在屏幕上分不开。")
        return 4
    # ★ 离线自测：**不进正常跑法**（十几遍真扫）。拦在量之前 —— 它跑的就是"量之前那几道门"。
    if a.selfcheck_gate:
        return selfcheck_gate(a, sys.argv[1:])

    # ★ **别让新的门复刻旧病**（@nova-8980 12:5x 的警告）：三个 `--expect-*` 都是"我手打一串数"，
    #   打歪一位就**永远比不上** —— 而"常数写坏了"和"对象真的不对"会长成一个样（三态共用一个词，
    #   今天栽过好几回的那格）。⇒ 先验**形状**，说清是哪一种，再谈比不比得上。
    # ★ 三态，不是两态（@iris-64a1 13:1x 量到的第二个入口，比 rc=2 那格更重）：
    #   `--expect-flags "$FLAGS"`（**变量没展开**，最常见的真实写法）⇒ 值**到了器手里**，
    #   而 `if a.expect_flags:` 把它当成"没给" ⇒ 照旧出数、照旧印「是」，那格只写「★ 没核」。
    #   ⇒ `flags_shape_bad("")` 那段防守**永不执行**（死代码 = 没人负责的租客）。
    #   这与 `--commit` 那格（"抄错也出数"）**逐字同形，换了根轴**。
    #   ⇒ 判据：**"没给"和"给了个空的"不是一件事**，四个常数一起改成三态（不挑着改）。
    for flag, val, n, name in (("--expect-corpus", a.expect_corpus, 16, "sha256 前16位"),
                               ("--expect-judge", a.expect_judge, 16, "sha256 前16位"),
                               ("--expect-tree", a.expect_tree, 40, "40位 tree sha")):
        if val is not None and not re.fullmatch(r"[0-9a-f]{%d}" % n, val):
            print("★ %s 给的**不是一个%s**（你给的是 %r，%d 个字符）⇒ **器还没开始量**（exit=7）。"
                  % (flag, name, val, len(val)))
            print("  ★ 这不是「对不上」，是**参数写坏了**：两件事共用一句'红'，就分不出是哪个了。")
            print("  ★ 抄常数的时候，长度对不对是**唯一能当场自查**的那一格 —— 所以先查它。")
            # ★ 出口码也**分开**（@nova-8980 12:5x 抓的）：我原先把这一格和"没点对象"一起塞进 4 ——
            #   **我刚在文字那一格治好的病（三态共用一个词），当场在出口码那一格复刻了一遍。**
            #   判准是**这是谁的错**：「常数打歪了」是**调用方的**错；「没点对象」是**那次调用没说清对象**。
            #   4 和 7 都停在"量之前"，所以对读数的影响一样 —— 但机器分得出，人不用去读中文才知道是哪种。
            return 7
    # ★ `--expect-flags` 走**同一条形状优先**的路（理由与上面三个常数完全相同）：
    #   "常数打歪了"和"真的对不上"不许共用一句红。形状 = 成对的 `--名 值`。
    if a.expect_flags is not None:
        bad = flags_shape_bad(a.expect_flags)
        if bad:
            print("★ --expect-flags 给的**不是一个旗标串**（%s）⇒ **器还没开始量**（exit=7）。" % bad)
            print("  ★ 这不是「对不上」，是**参数写坏了**：两件事共用一句'红'，就分不出是哪个了。")
            print("  ★ 形状是成对的 `--名 值`，例如：")
            print("      --expect-flags '--min-len 1 --face whole --dedup raw "
                  "--v1ref keep --unit gone --ladder norm'")
            return 7
        eff = flagline(a)
        if a.expect_flags != eff:
            print("★ 生效旗标串对不上 ⇒ **拒绝出数**（exit=8）。"
                  "`数 = f(对象, 语料, 判据, ★旗标)`——第四个自变量原来一个都没钉：")
            print("  期望 --expect-flags %s" % a.expect_flags)
            print("  实际生效旗标      %s   ← **解析后的生效值**，不是你写的拼法" % eff)
            print("  ★ 漏写一个旗标 ⇒ 另一个数，而屏幕上与「照抄的那一跑」逐字节同形；"
                  "这一格就是让那种跑**红得起来**。")
            return 8
    docs = V.load()
    if docs is None:
        print("语料不在 ⇒ 什么都没查（exit=2）。先跑 tools/fetch_chanlun108.py")
        return 2
    # unit=gone 才建索引：它是"分母怎么定义"那一格，不是装饰。
    a.corpus = V.Corpus(docs, V.norm) if a.unit == "gone" else None

    d = tree_dir(a.tree)
    base = d or V.ROOT
    try:
        print("量法   口径参数：commit=%s · unit=%s · min-len(norm后)=%d · face=%s · "
              "dedup=%s · v1_ref=%s · ladder=%s"
              % (a.tree, a.unit, a.min_len, a.face, a.dedup, a.v1ref, a.ladder))
        obj_text, obj_is_obj = which(a.tree)
        print("对象   %s" % obj_text)
        # ★★ 对象那一行里，**是身份的是 `→ tree <40位>`，不是前面那个名字**（@nova-8980 12:5x 的刀）：
        #   `git tag 05f3e24 335e3a3` —— 之后的 `--commit 05f3e24` **拼法一字不变**，
        #   解析出来的却是另一棵树，而门照印「是」。⇒ 名字是**给人看的**，树是**给判据用的**。
        m = re.search(r"→ tree ([0-9a-f]{40})", obj_text)
        got_tree = m.group(1) if m else ""
        if a.expect_tree is not None and got_tree != a.expect_tree:
            print("★ 树对不上 ⇒ **拒绝出数**（exit=6）。名字一样**不等于**对象一样：")
            print("  期望 --expect-tree %s" % a.expect_tree)
            print("  实际（对象自己说的）  %s" % (got_tree or "没有树（就地跑）"))
            print("  ★ 实测那条刀：`git tag 05f3e24 335e3a3` ⇒ 同一个拼法，树从 de39cdf7 变成"
                  " 45056e42，数从 331/302 变成 400/360 —— 上一版门在这跑里印「是」。")
            return 6
        fp, fbytes = V.fingerprint(docs)
        if a.expect_corpus is not None and fp != a.expect_corpus:
            print("★ 语料指纹对不上 ⇒ **拒绝出数**（exit=3）。这一格是门，不是装饰：")
            print("  期望 --expect-corpus %s" % a.expect_corpus)
            print("  实际（%d 字节语料）      %s" % (fbytes, fp))
            print("  ★ 换个 QL_CORPUS 指进来，这支器照样跑、照样印一个 sha256、照样出数 —— "
                  "只有这道门能把「看起来验过」和「验过」分开。")
            return 3
        print("语料   sha256:%s%s" % (
            fp, "  （已核：== --expect-corpus）" if a.expect_corpus
                else "  （★ **没核**：没给 --expect-corpus，这个 sha256 只是印出来的）"))
        # ★★ 第三个输入：**判据自己**（@nova-8980 量出的第二个洞）。
        #   这行**无条件印**（@nova-8980 12:5x 的 ①）："没核"和"核过"必须**分开印**，
        #   否则又回到"看起来验过"那一格 —— 和语料那行同一个模样。
        jsha, jblob, jpath = judge_id()
        if a.expect_judge is not None and jsha != a.expect_judge:
            print("★ 判据指纹对不上 ⇒ **拒绝出数**（exit=5）。门原来只核两个输入，可"
                  "**读数由三个决定**：")
            print("  期望 --expect-judge %s" % a.expect_judge)
            print("  实际（我导进来的那个文件）     %s" % (jsha or "拿不到"))
            print("  ★ 判据一换、器一字节不动，数就变：旧判据 `b31431b3` ⇒ 331/302→336/307；"
                  "`norm` 改成恒等 ⇒ →365/333。")
            print("  ★ 而**上一版门在这两跑里都印「是」、rc=0** —— 一个换错判据的人会拿到一张"
                  "自称验收通过、数却不对的表。")
            return 5
        if jsha is None:
            print("判据   ★ **拿不到判据文件**（`V.__file__`=%r）⇒ 这个数连「谁算的」都说不出来"
                  % (jpath,))
        else:
            print("判据   %s sha256:%s（git blob %s）%s"
                  % (os.path.basename(jpath), jsha, jblob,
                     "  （已核：== --expect-judge）" if a.expect_judge
                     else "  （★ **没核**：没给 --expect-judge，这个 sha256 只是印出来的）"))
        # ★★ 验收判据做成**专用单值**（@iris-64a1 14:3x 量出的洞 + 她先提的"门挪到输出匹配"）：
        #   ① 洞：`--commit .` 是**正当用法**（该跑、该 exit=0），但它不是任何一个对象
        #      ⇒ **换个拼法就绕过"不写对象"那道门**（明写 `.`，照样出数）。
        #      所以门不能只装在"参数写没写"上，要装在这个数**是什么**上。
        #   ② 但**判据不许借 `★`**：实测**验收命令自己**也印 ★ ——
        #      `★ 这一支不判对错…`（census 那段说明）在干净验收跑的第 15 行，
        #      按"输出里没有 ★ 行"判会把**正确的那跑**判红（@iris-64a1 三跑实测：正确跑 ★=1）。
        #      **借别人也在用的字符当接口，正是这仓杀掉过的病。**
        #   ⇒ 一行单值：`验收可用=是` / `验收可用=否`。检查方：`grep -q '验收可用=是'`。
        #      它**能失败**：少给一个 --expect-corpus 就会翻成 否（下面的 else 会说出少了哪一条）。
        # ★ 三态（`is not None`）：**"没给"和"给了个空的"不是一件事**（@iris-64a1 13:1x 量的第二个
        #   入口）—— `--expect-flags "$FLAGS"`（变量没展开）值**到了器手里**，被 `if a.expect_flags:`
        #   当成"没给" ⇒ 照旧出数。给了空的现在走形状那格（exit=7），走不到这儿。
        corpus_ok = a.expect_corpus is not None   # 对不上在前面已 exit=3，走到这儿就是核过了
        judge_ok = a.expect_judge is not None     # 对不上在前面已 exit=5，走到这儿就是核过了
        tree_ok = a.expect_tree is not None       # 对不上在前面已 exit=6，走到这儿就是核过了
        flags_ok = a.expect_flags is not None     # 对不上在前面已 exit=8，走到这儿就是核过了
        # ★★ @nova-8980 13:15 裁决：`--expect-flags` **并进**这个条件（我原来那处"故意不对称"被打回）。
        #   她的两条理由，都写在下面（我照收，别再"行内自带披露"那套）：
        #   ① 「是」的语义 = **这一跑可以当验收读数引用**。旗标不钉 ⇒ 它复现的是**某个**数、
        #      不是那张卡上写的那个数 —— 本卡的立卡理由就是这条：同一句"全默认"在这支器的
        #      8 个历史版本上给出**三个数**（366/334 · 356/325 · 347/316），**光旗标就能挪数**。
        #   ② **一个单值的含义，不许取决于"某个可选参数给没给"** —— 否则「是」有两种读法，
        #      正是今晚在治的病（同一句担保，作用域比它钉住的事实大）。
        #   ★ 顺带把立卡那件事接上了：那次事故**没有加旗标，只翻了 `--v1ref` 的默认值**。
        #     `8` 号门核的是**生效值**，默认值就在那串里 ⇒ 默认一翻，同一条命令的期望串立刻对不上。
        #     ★ 但**只在"命令没写那个旗标"时**（@nova-8980 13:1x 的边界，我签）：命令把
        #     `--v1ref keep` 写全了，默认翻了数也不变、**也不该红** —— 那不是漏洞是正确，
        #     可两次"不红"长得一模一样（一次是没抓到、一次是本该不红）⇒ 写清、并成对地量（见卡）。
        tags, why = [], []
        if not obj_is_obj:
            tags.append("对象不是 sha")
            why.append("对象不是任何一个 sha（就地扫工作目录 ⇒ 这个数绑的是"
                       "**你脚下那份树的快照**，换个人、换个脏法就换个数）")
        if not corpus_ok:
            tags.append("语料没核")
            why.append("没给 --expect-corpus（语料只是印出来的，**没核过**）")
        if not judge_ok:
            tags.append("判据没核")
            why.append("没给 --expect-judge（**判据**只是印出来的，没核过 —— "
                       "而判据一换数就变，门原来在这两跑里都照印「是」）")
        if not tree_ok:
            tags.append("树没核")
            why.append("没给 --expect-tree（**对象名**只是拼法，没核过它指的是哪棵树 —— "
                       "`git tag 05f3e24 <别的提交>` 之后，拼法一模一样、数是另一棵树的）")
        if not flags_ok:
            tags.append("旗标未钉")
            why.append("没给 --expect-flags（**旗标/默认值**只是印出来的，没核过 —— "
                       "它就是这个第四个自变量：同一句「全默认」在 8 个版本上给出三个数，"
                       "差的是 `--v1ref` 的默认翻过一面）")
        flagseg = "生效旗标 %s（%s）" % (
            flagline(a),
            "已核 --expect-flags" if flags_ok else "★ 没核 --expect-flags")
        if not tags:
            print("验收可用=是    （树=%s · 语料 sha256:%s 已核 · 判据 sha256:%s 已核 · %s）"
                  % (got_tree, fp, jsha, flagseg))
        else:
            # ★ 单值那一行现在**带名字**（`验收可用=否（旗标未钉）`）：@nova-8980 要的退路 ——
            #   老命令跑新器会变红，但那声红是**准确的**且**说得出原因**，不用重写任何老卡。
            print("验收可用=否    （%s）—— 不是「跑不动」（这跑是正当用法、"
                  "exit 照常），是**这张表不能当验收读数**：" % " · ".join(tags))
            for w in why:
                print("               · %s" % w)
            print("               · %s" % flagseg)
            # ★ 这段**不许把判据原样打出来**（我第一版就打了，当场自伤）：判据是 grep 一个单值，
            #   而我把那个单值写进了这段说明里 ⇒ **器自己的说明被自己的判据搜到** ⇒ 否也判"过"。
            #   实测：②③ 两跑明明印的是 否，`grep -q '验收可用=是'` 却在**说明文字**里命中了。
            #   ⇒ 这里只说"上面那一行必须是「是」"，**一个字都不许拼出那个 token**。
            print("               判据＝**上面那一行**行首的 `验收可用` 单值必须是「是」"
                  "（★ 别拿 `★` 当判据 —— 正确的那跑自己也印 ★）")
        print()
        rows, tot = tally(base, a)
        for name, n, k in rows:
            print("  %-8s %4d 处 / %4d 条" % (name, n, k))
        print("  %-8s %4d 处 / %4d 条" % ("合计", tot[0], tot[1]))
        print()
        # ★ 收尾行**不许并列两把梯子**（@atlas-791f 12:11 抓的）：
        #   原来这行印的是字面量 `← 卡面那四格是 331 / 302` ——
        #   **形状是比较，实质是断言**：换一档它照印 331/302，读者只会去找一个不存在的差错。
        #   这正是本卡在治的病（数印出来了、分母没跟来），复发在为治它而刚写的器里。
        #   ⇒ 同一棵树、同一口径参数，**只换 --ladder 再跑一遍**，印出来的才是"比较"。
        #   这个 Δ 是**能失败的数**（阶梯若失效它会是 0），不是字面量。
        other = "norm" if a.ladder == "norm+ellipsis" else "norm+ellipsis"
        here = a.ladder
        a.ladder = other
        try:
            orows, otot = tally(base, a)
        finally:
            a.ladder = here
        print("  同一棵树、同一口径参数，**只换 --ladder %s** ⇒ %d 处 / %d 条"
              "（差 %+d 处 / %+d 条）"
              % (other, otot[0], otot[1], otot[0] - tot[0], otot[1] - tot[1]))
        om = dict((r[0], r) for r in orows)
        print("  逐格：%s" % " · ".join(
            "%s %+d/%+d" % (r[0], om[r[0]][1] - r[1], om[r[0]][2] - r[2])
            for r in rows if r[0] in om))
        if a.unit == "all":
            print("  ★ unit=all 时两档**必然**同数（分母不判「原文有没有」，逐段档无从参与）"
                  "—— 这个 0 有理由，不是阶梯坏了。")
        print()
        print("★ 这一支不判对错，只把口径跑成数。判据看 tools/quotes_census.py 的三箱。")
    finally:
        if d:
            shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
