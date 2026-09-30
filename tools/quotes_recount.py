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

八个旋钮（就是这一支的全部输入，多一个都没有）：
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

退出：0 跑完 · 2 语料不在（**查不了 ≠ 通过**）· 3 语料指纹对不上（--expect-corpus）
      · 4 没点对象（`--commit`/`--tree` 一个都没写）—— 见下面 `--commit` 那格
      · 7 某个 `--expect-*` 给的不是它该有的长度 —— **器还没开始量**。
          4 和 7 都停在"量之前"，可**原因不同**（谁没说清对象／谁把常数打歪了），
          而"共用一句红"正是今天反复栽的那格 —— 文字分了，出口码也得跟着分
      · 5 **判据**指纹对不上（--expect-judge）—— 数和 3 **分开出口**：3 与 5 都"拒绝出数"，
        但**原因不同**，而今天反复栽的就是"红是对的、原因是错的"那一格
      · 6 **对象解析出来的树**对不上（--expect-tree）—— 名字一样 ≠ 对象一样

★★ 验收判据：**`grep -q '验收可用=是'`**（输出里那一行单值）。三个条件**必须写成"印了且 = 是"**：

```
验收可用=是        ✓ 过
验收可用=否        ✗ 红（下面会说出少了哪一条：对象不是 sha ／ 语料没核 ／ 判据没核）
（没有这一行）      ✗ 红  ← **旧版器就是这一格**：判据若写成"没有 否就算过"，它静默通过
```
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


def main():
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
    ap.add_argument("--expect-corpus", default="", metavar="<sha256前16位>",
                    help="语料指纹对不上就 exit=3。不给 ⇒ 那行会自报「★ 没核」。")
    # ★ 第二个洞（@nova-8980 12:4x 量到、@atlas-791f 12:5x 独立变异复现）：
    #   门核的是「对象 + 语料」，可这支器的数**由三个输入决定** —— 判据是第三个。
    #   ⇒ 照 --expect-corpus 那把尺再钉一次（**不另发明概念**）：同一个模样、同一个出口形态。
    ap.add_argument("--expect-judge", default="", metavar="<sha256前16位>",
                    help="判据 verify_quotes.py 的指纹对不上就 exit=5。"
                         "不给 ⇒ 那行会自报「★ 没核」。")
    # ★ 第三个洞（@nova-8980 12:5x）：`git tag 05f3e24 335e3a3` ⇒ 拼法不变、对象换了、门照印「是」。
    #   ⇒ 前三道门都钉在「你写了什么」上，这一道钉在「你指的是哪棵树」上。
    ap.add_argument("--expect-tree", default="", metavar="<40位 tree sha>",
                    help="对象解析出来的树 sha 对不上就 exit=6。"
                         "不给 ⇒ 判据那格会说出「树没核」。")
    a = ap.parse_args()

    if a.tree is None:
        print("★ 没点对象 ⇒ **拒绝出数**（exit=4）。这支器量的是「某个提交的树」，")
        print("  不是「此刻谁的工作目录」—— 而这两件事**只差一个漏写的参数**：")
        print()
        print("    --commit <sha|tree>   要跟别人比数 ⇒ 用这个")
        print("    --commit .            确实要扫**当前工作目录**（含未跟踪）⇒ 也请明确写出来")
        print()
        print("  ★ 不写也能跑 = 「抄错也出数」：粘贴时漏掉对象，和一次合法读数在屏幕上分不开。")
        return 4
    # ★ **别让新的门复刻旧病**（@nova-8980 12:5x 的警告）：三个 `--expect-*` 都是"我手打一串数"，
    #   打歪一位就**永远比不上** —— 而"常数写坏了"和"对象真的不对"会长成一个样（三态共用一个词，
    #   今天栽过好几回的那格）。⇒ 先验**形状**，说清是哪一种，再谈比不比得上。
    for flag, val, n, name in (("--expect-corpus", a.expect_corpus, 16, "sha256 前16位"),
                               ("--expect-judge", a.expect_judge, 16, "sha256 前16位"),
                               ("--expect-tree", a.expect_tree, 40, "40位 tree sha")):
        if val and not re.fullmatch(r"[0-9a-f]{%d}" % n, val):
            print("★ %s 给的**不是一个%s**（你给的是 %r，%d 个字符）⇒ **器还没开始量**（exit=7）。"
                  % (flag, name, val, len(val)))
            print("  ★ 这不是「对不上」，是**参数写坏了**：两件事共用一句'红'，就分不出是哪个了。")
            print("  ★ 抄常数的时候，长度对不对是**唯一能当场自查**的那一格 —— 所以先查它。")
            # ★ 出口码也**分开**（@nova-8980 12:5x 抓的）：我原先把这一格和"没点对象"一起塞进 4 ——
            #   **我刚在文字那一格治好的病（三态共用一个词），当场在出口码那一格复刻了一遍。**
            #   判准是**这是谁的错**：「常数打歪了」是**调用方的**错；「没点对象」是**那次调用没说清对象**。
            #   4 和 7 都停在"量之前"，所以对读数的影响一样 —— 但机器分得出，人不用去读中文才知道是哪种。
            return 7
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
        if a.expect_tree and got_tree != a.expect_tree:
            print("★ 树对不上 ⇒ **拒绝出数**（exit=6）。名字一样**不等于**对象一样：")
            print("  期望 --expect-tree %s" % a.expect_tree)
            print("  实际（对象自己说的）  %s" % (got_tree or "没有树（就地跑）"))
            print("  ★ 实测那条刀：`git tag 05f3e24 335e3a3` ⇒ 同一个拼法，树从 de39cdf7 变成"
                  " 45056e42，数从 331/302 变成 400/360 —— 上一版门在这跑里印「是」。")
            return 6
        fp, fbytes = V.fingerprint(docs)
        if a.expect_corpus and fp != a.expect_corpus:
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
        if a.expect_judge and jsha != a.expect_judge:
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
        corpus_ok = bool(a.expect_corpus)   # 对不上在前面已 exit=3，走到这儿就是核过了
        judge_ok = bool(a.expect_judge)     # 对不上在前面已 exit=5，走到这儿就是核过了
        tree_ok = bool(a.expect_tree)       # 对不上在前面已 exit=6，走到这儿就是核过了
        if obj_is_obj and corpus_ok and judge_ok and tree_ok:
            print("验收可用=是    （树=%s · 语料 sha256:%s 已核 · 判据 sha256:%s 已核）"
                  % (got_tree, fp, jsha))
        else:
            why = []
            if not obj_is_obj:
                why.append("对象不是任何一个 sha（就地扫工作目录 ⇒ 这个数绑的是"
                           "**你脚下那份树的快照**，换个人、换个脏法就换个数）")
            if not corpus_ok:
                why.append("没给 --expect-corpus（语料只是印出来的，**没核过**）")
            if not judge_ok:
                why.append("没给 --expect-judge（**判据**只是印出来的，没核过 —— "
                           "而判据一换数就变，门原来在这两跑里都照印「是」）")
            if not tree_ok:
                why.append("没给 --expect-tree（**对象名**只是拼法，没核过它指的是哪棵树 —— "
                           "`git tag 05f3e24 <别的提交>` 之后，拼法一模一样、数是另一棵树的）")
            print("验收可用=否    —— 不是「跑不动」（这跑是正当用法、exit 照常），"
                  "是**这张表不能当验收读数**：")
            for w in why:
                print("               · %s" % w)
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
