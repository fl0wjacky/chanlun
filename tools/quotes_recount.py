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

十三个旋钮（就是这一支的全部输入，多一个都没有；`--commit` 还收旧拼法 `--tree`，`-h` 不算）：
★ 这个数**又数错过一次**（写"十一"的时候下面其实是十三个）：散个数会烂，**数的定义是
  `COUNT_AXES + OTHER_AXES + MODE_AXES`**，自查 9 号管得住"有没有登记"、管不住这句话里的数 ——
  **散文里的计数是没人负责的租客**，所以加旗标时**连这句话一起改**（本轮 `--speaker`/`--expect-speaker`）。
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
    --speaker <tsv>      ★ **旁档**（说话人判词）：它**不改数，它归类数**。
                         不变量**单向**：旁档**每一行**都必须联上器数出来的一条
                         （悬空的判词是错，不是「未判」）；器 → 旁档**不要求**
                         （没判到的落「（空）=没判过」，旁档自己标 `未判` 的另算一态）。
                         任何一格不成 ⇒ **exit=11、不出数**，并在印出来那行**点名是哪一张脸**。
                         ★ 联结键 = `sha1(引文**原始串** utf-8)` 前 16 位 —— 对**原始**串算，
                           不经任何转义（旁档第 2 栏是**显示用**的，它把 `\n` 换成了 `⏎`，
                           拿它去联会在含换行的键上**全查不到**，而"联不上"长得就像"它没有"）。
                         ★ 列**按表头里的名字取**（`# columns` 那一行），**不按位置取**：
                           按位置取，旁档里加一栏就会静默错读一整列，而屏幕上数还是对的。
                         ★ 它是**非计数轴**（`OTHER_AXES`）且**点名豁免探针**（`PROBE_EXEMPT`）：
                           换一份旁档 = 换一次测量，不是旋钮（同 `--commit` 那一格）。
    --expect-speaker <语义指纹前16位>
                         旁档的**语义指纹**对不上 ⇒ **exit=11、不出数**。
                         ★ 指纹对**排序后的 `(key_sha1, 判词)` 对**算 —— **不是**文件 sha256。
                           @iris-64a1 给旁档加了一行 `# columns` 机器可读表头，**一个判词都没改**，
                           文件 sha256 就变了 ⇒ **字节 sha 是"文件长相"的函数**，只能当
                           「我读的是不是同一份文件」的对角线（所以那一行把**文件名**跟它印在一起），
                           **不能当门**。@nova-8980 的仓规：**凡当门用的指纹，必须指名它的定义域。**
                         ★ 它与旁档自陈的 `# 分母：N 处 / M 条`、`# tree <40位>` 是三格**独立**的门：
                           旁档那一行自己写着"当场算、当场印，非写死" ⇒ 它是**坐标**，不是注释。
                           换一档旗标（`--face`/`--ladder`/`--min-len`）时**旁档一行不变、逐行联结照样全中**，
                           只有"分母/对象"那两格拦得住 —— 那正是"同一份旁档配了另一套旗标"这个坑。
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
     ★ ⑤（旁档读入侧）：正臂必须出数、**七条脸各喂一次红**（悬空/表头/未声明的值/重复键/
       分母对不上/对象对不上/指纹）+ ⑤e「探针那一跑**没出数**」那一口。
       ★ 为什么单列一块：读入侧一口气加了七张脸，只印不喂 ⇒ 那七张脸本身就成了**一批新的
         "不可能失败的门"**（④ 那一课：刚落地这条修法的人最容易在新那一层复犯旧病）。
       ★ 实测两处红（我跑的）：把 ⑤e 那支退回原样 ⇒ ⑤e 红（病名点回「登记错」）；
         把「（空）」那一行的类键退回成它的标签 ⇒ **正臂红**（等式印「不成立（器自己坏了）」）——
         后者正是我第一版真犯的 bug，**是 ⑤ 正臂先抓出来的**。
 11  **旁档这一格拒绝出数**（`--speaker` / `--expect-speaker`）。
     ★ 一个出口码，**十一张脸**（都在印出来那行点名）：读不到 / 表头 / 栏数不齐 / 空表 /
       重复键 / 未声明的值 / 悬空 / 对象对不上 / 分母对不上 / 指纹 / 没给旁档却给了期望值。
     ★ 为什么不拆成十一个码：它们不是"谁的错"各不相同那一类（4/7/9 那种），
       而是**同一条流水线的十一个阶段** —— 拦下来的动作是同一个（不出数）。
       与"三态共用一个词"的区别在**脸**：出口码管"拒绝出数"，印出来那行管"为什么"，
       两者都点名 ⇒ 不混。（若哪天有一格需要**别人自动区分**，再拆码。）
     ★ 故意红（实测）：改坏一位 `key_sha1` ⇒ `脸 = 悬空`；`--face literal` 配同一份旁档
       ⇒ `脸 = 分母对不上`（**逐行联结照样全中**，只有这一格拦得住）；
       `--expect-speaker` 不给 `--speaker` ⇒ `脸 = 没给旁档却给了期望值`。

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
import argparse, collections, hashlib, io, os, re, shutil, subprocess, sys, tempfile

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


def _sites(base, a):
    """**逐处**枚举：(格, 引文原文)。这是落点判定的**唯一一份**实现 ——
    `tally()`（器印的合计）与`说话人轴`（三栏的分母）都从它派生。

    ★ 为什么抽这一层（2026-09-30，本卡）：说话人轴要印「331 处的三栏」，
      而 331 是器**自己的**数。若三栏另写一份"怎么算一处"的筛选，两份会漂
      —— 本仓今晚反复栽在「两份手写声明」上（`COUNT_AXES` 那格、`--expect-flags` 的词汇表）。
      ⇒ 判据：**分母与合计必须出自同一次扫描**，不是"两次扫描恰好相等"。

    ★ 产出顺序 = `CELLS` 的顺序、格内 `sorted(files)`，最后 `config.py`
      （`tally` 的行序靠它）；不存在的格不产出（⇒ 行里没有它，与旧 `count()` 的 `(0,0)` 同效果）。
    """
    for cell in CELLS:
        d = os.path.join(base, cell)
        if not os.path.isdir(d):
            continue
        for root, _dd, files in os.walk(d):
            if a.v1ref == "skip" and "v1_ref" in root:
                continue
            if any(("/%s" % x.split("/")[-1]) in root or root.endswith(x)
                   for x in V.SKIP if x.split("/")[-1] != "v1_ref" or a.v1ref == "skip"):
                continue
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                t = io.open(os.path.join(root, f), encoding="utf-8").read()
                for body in ([t] if a.face == "whole" else literal_bodies(t)):
                    for m in Q.finditer(body):
                        q = pair(m)
                        if len(V.norm(q)) < a.min_len:
                            continue
                        if found(q, a):
                            continue                  # 原文里有 ⇒ 不算「找不到」（按 --ladder）
                        yield cell, q
    # 仓根的 config.py（不是一级目录 ⇒ `CELLS` 那轮走不到它，但它必须进合计）
    cf = os.path.join(base, "config.py")
    if a.face == "whole" and os.path.isfile(cf):
        t = io.open(cf, encoding="utf-8").read()
        for m in Q.finditer(t):
            q = pair(m)
            if len(V.norm(q)) < a.min_len:
                continue
            if found(q, a):
                continue
            yield "config.py", q


def _key(q, a):
    """条那一把钥匙：`--dedup raw` 用原文，`norm` 用规范化后的。"""
    return q if a.dedup == "raw" else V.norm(q)


def tally(base, a, sites=None):
    """整表跑一遍 ⇒ (rows, tot)。rows = [(名字, 处, 条)]，合计由 rows 现加。

    **抽成函数是为了能跑第二遍**：收尾那行要比"换一档"的差，就得真跑两次。
    ★ `sites` 可传入**已经扫好的落点**（主流程要拿同一份去印说话人轴）——
      「分母与合计出自同一次扫描」不是效率问题：两次扫描恰好相等 = 漂了没人红。
    """
    seen, order = {}, []
    for cell, q in (list(_sites(base, a)) if sites is None else sites):
        if cell not in seen:
            seen[cell] = [0, set()]
            order.append(cell)
        r = seen[cell]
        r[0] += 1
        r[1].add(_key(q, a))
    rows = [(c, seen[c][0], len(seen[c][1])) for c in order]
    return rows, (sum(r[1] for r in rows), sum(r[2] for r in rows))


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


# 「面」的机械定义：**引文出现在哪几格** —— 只看落点，不看内容。
#   ★ 这是**出现**的属性，不是引文的属性：同一条引文可以两面都出现 ⇒ 单列「两面」，
#     不许折进任一面（折进去 = 把一个"跨"写成一个"是"）。@iris-64a1 量的：main 上 457 处里
#     363 处落在代码面 —— 那些「」本来就不是在引谁，而 (a)/(b) 的判据只在卡片面有定义。
FACE_CELLS = (("卡片面", ("cards", "render")), ("代码面", ("core", "tools", "config.py")))


# 说话人轴的**类别集**（一份声明，写死在器里 —— @iris-64a1：**枚举写在读入侧代码里，不从数据里学**）。
#   ★ 从数据里反推枚举会**静默剪掉还没出现过的值**（旁档里 `未判` 现在可能 0 条 ⇒ 从数据学就把它剪了），
#     而"没给"与"给了个空的"共用一张脸正是本卡要治的那格。
#   ★ 顺序 = 印出来的顺序；`未判` 与 `没判过` **两个态**（一百〇二），不许合并。
#   ★ 旁档里出现**没在这里声明的值** ⇒ 不是"忽略"，是**报错并点名那个值**（下一笔的读入侧照这条）。
SPEAK_CLASSES = (
    ("a", "引文失真：本来是缠师的话，字句不对（**只在卡片面**）"),
    ("b", "引号用错：本来就不是缠师的话（**只在卡片面**）"),
    ("省略", "忠实省略：缠师原话＋忠实省略号（**档位的账**）"),
    ("配对伪影", "**器的账**：配对吞了源码（坏的是键，不是写法）"),
    ("自陈整理版", "上一行自陈「非逐字」（机器判据到不了）"),
)
SPEAK_UNDECIDED = ("未判", "没判过")


def _pad(t, w):
    """按**显示宽度**补空格（CJK 算 2 列）—— 不然对齐是按字符数对齐的，屏幕上是斜的。"""
    d = sum(2 if ord(c) > 0x2E80 else 1 for c in t)
    return t + " " * max(1, w - d)


# ── 旁档（说话人判词）读入侧 ──────────────────────────────────────────────────
#   ★ 这一格治的还是同一件事：**「没给」与「给了个空的」共用一张脸**。⇒ 下面几种**分开报**，
#     因为它们的修法各不相同（合起来报 = 没报）：
#       没给 --speaker ／ 读不到 ／ 表头不合格 ／ 栏数不齐 ／ 有表头没数据行 ／ 重复键 ／
#       未声明的值 ／ 悬空行 ／ 对象对不上 ／ 分母对不上 ／ 指纹对不上
#   ★ 出口**只有一个**（exit=11），但**脸各不相同**：出口码管"拒绝出数"，印出来那行管"为什么"。
#     一个出口码叫不出十一种病因 —— 今晚「三态共用一个词」已经是老病，别在新那一层复犯。
SPEAK_HDR = "# columns"
SPEAK_NEED = ("判词", "key_sha1")
# ★ 旁档里「没判过」那一态写成**空串**（@iris-64a1 15:2x 表头注解：「（空）=没判过」），
#   而 `未判` 是**另一态**（「判过·判不了」）。两个不许合并 —— `SPEAK_UNDECIDED` 那两格。
SPEAK_EMPTY = ""
SPEAK_EMPTY_LABEL = "（空）"
SPEAK_DECLARED = tuple(k for k, _w in SPEAK_CLASSES) + ("未判", SPEAK_EMPTY)
# ★ 面：旁档那一列写 `混合`，器算出来写 `两面` —— **同一个东西两个名字**。
#   在读入侧对齐（一处声明，两个名字都收），**不改旁档、也不改器的算法**：
#   名字是给人看的，判据是那个集合本身。
FACE_ALIAS_2 = ("两面", "混合")
FACE_COLS = ("卡片面", "代码面", "两面")


def _face_names(f):
    """列名 → 它认的**全部**拼法（唯一一处别名声明）。"""
    return FACE_ALIAS_2 if f == FACE_COLS[2] else (f,)


def speak_key(q):
    """旁档的联结键：`sha1(原始引文 utf-8).hexdigest()[:16]`。

    ★ 规格**不是我猜的**：@iris-64a1 给了两条算例，我当场反算、**逐位相同**
      （`查不出来不算通过` ⇒ `3e63a74d7d8a76644becabba5bf85b9526347da8`）。
      **无 strip、无 norm、无换行替换** —— 任何"顺手清一下"都会让 285 行全部联不上，
      而那时候报出来的脸长得就像"旁档写错了"（旁档 :29 记的正是这一类：**联不上不报错，
      它长得就像「它没有」**）。
    ★ 全长算、**截断在读入侧**：旁档哪天改成 40 位，只动这一处，不动"算法"。
    """
    return hashlib.sha1(q.encode("utf-8")).hexdigest()[:16]


def _speak_class_of(v):
    """旁档 `判词` 的值 → 声明里的类名（`None` = **没声明**）。

    ★ 值可以带一个括号注解（实测：`配对伪影（对象完好·键含源码语法）` /
      `自陈整理版（上一行写明非逐字·意思忠实）`）—— 那是**同一个类名 + 注解**，不是两个类
      ⇒ 认法：**恰好等于类名**，或**以 `类名（` 开头且以 `）` 结尾**。
    ★ 不许用裸前缀认（`v.startswith(name)`）：那会让 `省略` 吃掉 `省略xx` 这种**另一个
      没声明的值**，而"没声明的值必须报错"正是这一格的判据（`SPEAK_CLASSES` 顶上写着）。
    """
    for name in SPEAK_DECLARED:
        if v == name:
            return name
        if name and v.startswith(name + "（") and v.endswith("）"):
            return name
    return None


def _speak_gloss(v, name):
    """注解那一截（`配对伪影（…）` → `…`）—— **照印**。

    ★ 旁档 :37 自己写了理由：那半句不能省 —— 名字若只写「配对伪影」，下一个人会读成
      "这 13 个地点没有引文" = **静默少报**。⇒ 注解不是装饰，是那半句的落点。
    """
    if name and v != name and v.startswith(name + "（") and v.endswith("）"):
        return v[len(name) + 1:-1]
    return ""


def _per_quote(sites):
    """引文 → 它出现在哪几格（**条的层面**）。

    ★ 只写这一份：分母（`条`）、面、旁档的覆盖数**全从它派生**。另抄一份 = 手写的第二处声明，
      而"两份手写声明会漂"这一课今晚已经上过（`COUNT_AXES` 那一段）。
    """
    per = {}
    for cell, q in sites:
        per.setdefault(q, set()).add(cell)
    return per


def _face_of(per):
    """条 → 面（`卡片面` / `代码面` / `两面`）。★ 面是**算出来的**，不是常量。

    ★ 撤回记录（@nova-8980 的反例，我照抄坐标）：我原来在这里印过一句
      「(a)/(b) 的**定义域 = 卡片面**」—— **错的**：`core/segment.py:8` 是 core/（代码面），
      而那个文件自己的 `:5` 写着「核心（第 67 课原文）：」⇒ 判词**合法地落在代码面**。
      ⇒ 「面」是**统计量**（这处引文出现在哪些格），不是"有没有定义"的判据；
        拿它当判据 = 拿统计量当判据（今晚第三次）。**器里没有、也不许有「定义域」这道门。**
    """
    out = {}
    for q, cs in per.items():
        card = bool(cs & set(FACE_CELLS[0][1]))
        code = bool(cs & set(FACE_CELLS[1][1]))
        out[q] = "两面" if (card and code) else ("卡片面" if card else "代码面")
    return out


def load_speaker(path, sites):
    """读旁档 → `(rec, err)`；`err = (脸, 说明行…)` ⇒ 调用方拒绝出数（exit=11）。

    ★ 列**按表头里的名字取，不按位置取**：按位置取，旁档里加一栏就会**静默错读一整列**，
      而屏幕上印出来的数还是对的（@iris-64a1 15:2x 就当场加过一行 `# columns`）。
    ★ 判据是**单向**的：旁档 → 器，**每一行都必须联上器数出来的一条**（悬空的判词是错，
      不是"未判"）；器 → 旁档**不要求**（没判到的进「未判」/「空」）。
      ⇒ 反向那道门会当场拒掉合法数据（@iris-64a1 的旁档判满 285 条，而器数出来是 331 处）。
    """
    keys = set(speak_key(q) for q in set(q for _c, q in sites))
    try:
        rawb = open(path, "rb").read()
    except OSError as e:
        return None, ("读不到", ["旁档读不出来：%s" % e,
                                "★ 「没给 --speaker」与「给了个读不到的」是**两件事**，这是第二件。"])
    try:
        txt = rawb.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, ("读不到", ["旁档不是 UTF-8：%s" % e,
                                "★ 字节解不开 ⇒ 后面每一格都无从谈起，不猜编码。"])
    lines = txt.split("\n")

    hdr_i = next((i for i, l in enumerate(lines) if l.startswith(SPEAK_HDR)), None)
    if hdr_i is None:
        why = ["旁档里**没有一行**以 `%s` 开头 ⇒ 列名拿不到，**拒绝按位置猜**。" % SPEAK_HDR,
               "★ 按位置取列 = 旁档加一栏就静默错读一整列，而屏幕上数还是对的。"]
        bad = [l for l in lines[:80] if "<TAB>" in l]
        if bad:
            why.append("★ 且我**看见了元凶**：第 %d 行里有**字面** `<TAB>`（四个字符，不是制表符）。"
                       "「人读那一行」与「机器读那一行」长得很像，读入侧**不替作者猜**："
                       % (lines.index(bad[0]) + 1))
            for l in bad[:3]:
                why.append("      %s" % l[:100])
        return None, ("表头", why)
    cells = lines[hdr_i].split("\t")
    if cells and cells[0].strip() == SPEAK_HDR:
        cells = cells[1:]
    elif cells:
        cells[0] = cells[0].strip()[len(SPEAK_HDR):].strip()
    names = [c.strip() for c in cells]
    miss = [n for n in SPEAK_NEED if n not in names]
    if miss:
        return None, ("表头", ["旁档表头缺**必需**的列名：%s" % "、".join(miss),
                              "表头给的是：%s" % names,
                              "★ 必需的两栏：`%s`（联结键，对**原始串**算）与 `%s`（判词）。"
                              % SPEAK_NEED])

    rows, bad_w = [], []
    for i, l in enumerate(lines, 1):
        if not l.strip() or l.startswith("#"):
            continue
        f = l.split("\t")
        if len(f) != len(names):
            bad_w.append((i, len(f)))
            continue
        rows.append(dict(zip(names, f)))
    if bad_w:
        return None, ("栏数不齐", ["旁档第 %s 行的栏数与表头不符（表头说 %d 栏）：%s"
                                 % ("、".join(str(i) for i, _n in bad_w[:6]), len(names),
                                    "、".join("%d 行有 %d 栏" % (i, n) for i, n in bad_w[:6])),
                                "★ 半对半错的旁档最危险：**读得下去**、数看着正常。"])
    if not rows:
        return None, ("空表", ["旁档有表头、**0 行数据** ⇒ 拒绝把它当「已判」。",
                              "★ 「没给旁档」与「给了个空的旁档」共用一张脸，正是这一格要治的病。"])

    dup = sorted(k for k, n in collections.Counter(r["key_sha1"] for r in rows).items() if n > 1)
    if dup:
        return None, ("重复键", ["同一个 `key_sha1` 出现多次：%s（共 %d 个键）"
                               % ("、".join(d[:16] for d in dup[:5]), len(dup)),
                               "★ **不取「最后一行赢」**：一条引文两个判词是一件要人裁的事，"
                               "不是一次静默覆盖（@iris-64a1 今晚就栽过一次「把末行的列当首行的」）。"])

    bad_v = []
    for r in rows:
        if _speak_class_of(r["判词"]) is None and r["判词"] not in bad_v:
            bad_v.append(r["判词"])
    if bad_v:
        return None, ("未声明的值", ["旁档 `判词` 里有**没在声明里**的值：%s"
                                   % "、".join(repr(v) for v in bad_v[:5]),
                                   "声明的是：%s"
                                   % "、".join(repr(x) if x else "（空串=没判过）" for x in SPEAK_DECLARED),
                                   "★ 不许「忽略」、也不许折成「未判」—— 枚举写死在读入侧，"
                                   "**不从数据里学**（从数据学 = 静默剪掉还没出现过的值）。"])

    dangling = [r for r in rows if r["key_sha1"] not in keys]
    if dangling:
        why = ["旁档有 %d 行**联不上器数出来的任何一条** ⇒ 拒绝出数（悬空的判词是错，不是「未判」）。"
               % len(dangling),
               "★ 单向不变量：旁档 → 器 **每一行**都必须联上；器 → 旁档 **不要求**。"]
        for r in dangling[:5]:
            why.append("      key_sha1 %s · 引文前20字 %s"
                       % (r["key_sha1"][:16], (r.get("引文") or "")[:20]))
        if len(dangling) > 5:
            why.append("      …还有 %d 行" % (len(dangling) - 5))
        why.append("★ 最常见的成因**不是**「旁档写错了」，是**两边口径不同**（换了旗标/换了对象/"
                   "键算错了）⇒ 这一格**先核坐标**（下面印的对象/分母），再怀疑内容。")
        return None, ("悬空", why)

    verdict = {}
    for r in rows:
        verdict[r["key_sha1"]] = _speak_class_of(r["判词"])
    sem = "\n".join("%s\t%s" % (r["key_sha1"], r["判词"])
                    for r in sorted(rows, key=lambda r: r["key_sha1"]))
    decl_tree = decl_denom = None
    for l in lines:
        if not l.startswith("#"):
            continue
        m = re.match(r"#\s*tree\s+([0-9a-f]{40})\s*$", l.strip())
        if m and decl_tree is None:
            decl_tree = m.group(1)
        m = re.search(r"分母[：:]\s*(\d+)\s*处\s*/\s*(\d+)\s*条", l)
        if m and decl_denom is None:
            decl_denom = (int(m.group(1)), int(m.group(2)))
    return {"path": path, "names": names, "rows": rows, "verdict": verdict,
            # ★ 两把指纹，**只有一把是门**（@nova-8980 15:3x 合成的仓规：
            #   凡当门用的指纹，必须指名它的定义域）：
            #   语义指纹（门）= 对**排序后的 `(key_sha1, 判词)` 对**算 ⇒ 加注释栏、调列序都不动
            #   字节 sha（对角）= 加一栏就会变，只能答"我读的是不是同一份文件"
            "fp_sem": hashlib.sha256(sem.encode("utf-8")).hexdigest()[:16],
            "sha_bytes": hashlib.sha256(rawb).hexdigest()[:16], "nbytes": len(rawb),
            "gloss": sorted(set(_speak_gloss(r["判词"], verdict[r["key_sha1"]])
                                for r in rows) - {""}),
            "decl_tree": decl_tree, "decl_denom": decl_denom,
            "uncovered": sorted(k for k in keys if k not in verdict)}, None


def _cut(t, w):
    """按**显示宽度**截断（`_pad` 的孪生：一个补、一个切，都按 CJK 算 2 列）。"""
    out, d = "", 0
    for c in t:
        d += 2 if ord(c) > 0x2E80 else 1
        if d > w:
            return out + "…"
        out += c
    return out


def speaker_axis(sites, tot, a, sp=None):
    """说话人轴：**双轴**（类别 × 面），**恒印**。

    缺「未判」这一栏，`合计 331 处` 就会被读成「**331 处引文失真**」—— **超额声明**。

    ★ 分母两把尺，**各带口径**（@nova-8980 裁定 + @iris-64a1 量）：
        处 = **不去重**（每次出现各算一次）⇒ 归类是**划分** ⇒ 各类可以对到合计（331）
        条 = **必须全局去重**（raw 钥匙 = 285）⇒ 302 是 **Σ逐格去重**，同一句横跨两格各记一次
             ⇒ 拿 302 拆栏，**每一栏都虚高，而总数看起来还是对的**（最难发现的那种错）
      ⇒ 判据（@nova-8980）：一个数能不能被归类拆分，看它的**去重范围**是否 ⊇ 归类范围。

    ★★ @nova-8980 15:0x 的**双轴**裁决：`面` 是**分母的一部分，不是注释**
      ⇒ 主数字**分行印两面**（三列：卡片面 / 代码面 / 两面），不许只印一个合计再附一行面表。
      ★ 三列而不是两列：`两面` 折进任一面都是把一个「跨」写成一个「是」。

    ★ 旁档未给 ⇒ **每一类都印 `—`**（**没给**），**不许印 0** —— 与 `--expect-*` 那三态同一课。
      给了 ⇒ 数字从旁档来；旁档没覆盖到的条落「**（空）=没判过**」，
      旁档自己标 `未判` 的落「未判 = 判过·判不了」—— **两个态分行印，不许合并**。
    """
    per = _per_quote(sites)
    raw = list(per)
    nrm = len(set(V.norm(q) for q in raw))
    face_of = _face_of(per)
    occ_of = collections.Counter(q for _c, q in sites)
    have = sp is not None
    cls_of = {}
    if have:
        for q in raw:
            # ★ 旁档没覆盖到的条 → **空**（没判过），不是 `未判`（判过·判不了）：两个态不许合并。
            cls_of[q] = sp["verdict"].get(speak_key(q), SPEAK_EMPTY)

    def counts(clsname):
        qs = [q for q in raw if cls_of.get(q) == clsname]
        return (sum(occ_of[q] for q in qs), len(qs),
                dict((f, (sum(occ_of[q] for q in qs if face_of[q] in _face_names(f)),
                          sum(1 for q in qs if face_of[q] in _face_names(f)))) for f in FACE_COLS))

    print("说话人轴（**双轴**：类别 × 面 · 恒印 —— 缺「未判」这一栏，「合计 %d 处」就会被读成"
          "「%d 处引文失真」）" % (tot[0], tot[0]))
    print("   分母：**处** = %d（不去重：每次出现各算一次）· **条** = 全局去重（raw 钥匙）= %d"
          "（norm 钥匙 = %d）" % (tot[0], len(raw), nrm))
    print("         ★ 不是 %d：那是 **Σ逐格去重**（同一句横跨两格各记 1）⇒ **只能说「处」**；"
          "条那一列必须走全局去重" % tot[1])
    if not have:
        print("   旁档   ★ **没给**（没写 --speaker）—— 「没给」不是「给了个 0」：下面是 `—`。")
    else:
        print("   旁档   %s · %d 行 · 覆盖 %d/%d 条 · 语义指纹 sha256:%s（%s）"
              % (sp["path"], len(sp["rows"]), len(raw) - len(sp["uncovered"]), len(raw),
                 sp["fp_sem"],
                 "已核：== --expect-speaker" if a.expect_speaker else "★ **没核**：没给 --expect-speaker"))
        print("          文件 sha256:%s（%d 字节）—— ★ **仅供对角**（同名文件改前/改后），"
              "**门没装在这把尺上**：加一栏、调列序都会让它变，而判词一个没改"
              % (sp["sha_bytes"], sp["nbytes"]))
        print("          ★ 单向不变量：旁档 → 器 **每行都要联上**（悬空 %d 行）·"
              " 器 → 旁档 **不要求**（未判/空照实印）" % 0)
        if sp["gloss"]:
            for g in sp["gloss"]:
                print("          ★ 旁档那条判词的**后半截**（不许丢）：%s" % _cut(g, 90))
    print("   类别 × 面（**处/条**；@nova-8980：面轴是**分母**，不是注释）")
    print("      %s%s%s%s%s"
          % (_pad("类别", 14) + _pad("（说明）", 34),
             _pad("卡片面", 11), _pad("代码面", 11), _pad("两面", 11), "合计"))
    unk = sum(1 for q in raw if cls_of.get(q) is None) if have else 0
    tot_occ = tot_q = 0
    # ★ 三格：**印出来的名字**（`（空）`）/ **说明** / **类键**（`""`）——
    #   第一版把「印的名字」当类键用，于是 `counts("（空）")` 永远数不到 `""`
    #   ⇒ 未覆盖的条**哪儿都没落**、那一行恒印 0/0，而等式印「不成立（器自己坏了）」。
    #   ★ 这恰好是这一格要治的病在器自己身上复发：「**没判过**」被写成 0，
    #     而 0 与「没给」共用一张脸。**是 ⑤ 正臂把它抓出来的**（喂红之前，先喂了一次绿）。
    lines_out = [(k, w, k) for k, w in SPEAK_CLASSES] + [("未判", "判过·判不了", "未判"),
                                                        (SPEAK_EMPTY_LABEL,
                                                         "没判过（旁档里是空串）", SPEAK_EMPTY)]
    for name, why, key in lines_out:
        if not have:
            cells = ["—" for _f in FACE_COLS]
            print("      %s%s%s%s%s%s"
                  % (_pad(name, 14), _pad(_cut(why, 32), 34),
                     _pad("—", 11), _pad("—", 11), _pad("—", 11), "—"))
            continue
        o, n, pf = counts(key)
        tot_occ += o
        tot_q += n
        cells = ["%d/%d" % pf[f] for f in FACE_COLS]
        print("      %s%s%s%s%s%d/%d"
              % (_pad(name, 14), _pad(_cut(why, 32), 34),
                 _pad(cells[0], 11), _pad(cells[1], 11), _pad(cells[2], 11), o, n))
    if have:
        pf = dict((f, (sum(occ_of[q] for q in raw if face_of[q] in _face_names(f)),
                       sum(1 for q in raw if face_of[q] in _face_names(f)))) for f in FACE_COLS)
        print("      %s%s%s%s%s%d/%d"
              % (_pad("合计", 14), _pad("", 34), _pad("%d/%d" % pf[FACE_COLS[0]], 11),
                 _pad("%d/%d" % pf[FACE_COLS[1]], 11), _pad("%d/%d" % pf[FACE_COLS[2]], 11),
                 tot[0], len(raw)))
        # ★ 等式**现在能核了**，但要说清它是**恒等式**：联结完整 + 值域闭合 ⇒ 它必然成立。
        #   真判据在**联结那一侧**（悬空/值域/表头/重复键），那几格都喂过红（见 --selfcheck-gate ⑤）。
        ok = (tot_occ == tot[0] and tot_q == len(raw))
        # ★ 措辞里**不许再套一层 `**`**：原来写成 `"**%s**"` 而值本身带着 `**` ⇒
        #   屏幕上成了 `****不成立（器自己坏了）****`，而 ⑤ 正臂那条正则当场就抽不到它
        #   （「抽不到」与「不成立」共用一张脸 —— 又是同一课）。
        print("   等式核（各类 + 未判 + 空 = 合计）：%d 处 / %d 条 = 合计 %d 处 / %d 条 ⇒ %s"
              % (tot_occ, tot_q, tot[0], len(raw),
                 "成立" if ok else "**不成立（器自己坏了）**"))
        print("         ★ 但它是**恒等式**（联结完整时必然成立）⇒ **它不是门**。"
              "门在联结那一侧，各喂过一次红。")
    else:
        print("   等式核（各类 + 未判 + 空 = 合计）：**没核** —— 旁档未给 ⇒ 每一类都是 `—`，"
              "这条等式**现在不可能失败**")
        print("         （「一条不可能失败的门不是门」：等旁档进来它才成为一条真判据。）")
    print("   面（引文**出现在哪几格** · 只看落点）：%s"
          % " · ".join("%s %4d 处 / %4d 条"
                       % (f, sum(1 for _c, q in sites if face_of[q] in _face_names(f)),
                          sum(1 for q in raw if face_of[q] in _face_names(f)))
                       for f in FACE_COLS))
    if have and "面" in sp["names"]:
        # ★ 两条**独立**的路算「面」（旁档自陈 vs 器的 `_sites()`）⇒ 逐条比，能失败。
        #   名字不同不算不同（旁档写 `混合`，器写 `两面`）—— 别名对齐在读入侧。
        dis = [r for r in sp["rows"]
               if r["面"] not in _face_names(face_of.get(_q_by_key(sites, r["key_sha1"]), ""))]
        print("   面（旁档自陈 vs 器算，逐条比）：一致 %d/%d%s"
              % (len(sp["rows"]) - len(dis), len(sp["rows"]),
                 "" if not dis else " · **不一致 %d**（前 3：%s）"
                 % (len(dis), "、".join("%s→%s" % (r["key_sha1"][:8], r["面"]) for r in dis[:3]))))
    assert len(raw) == sum(1 for q in raw if face_of[q]), "面分类漏项"
    assert sum(len([q for q in raw if face_of[q] in _face_names(f)]) for f in FACE_COLS) \
        == len(raw), "面分类不划分"
    if have:
        assert unk == 0, "有条没落到任何一类（读入侧漏了态）"


def _q_by_key(sites, k):
    """联结键 → 引文原文（由 sites 现算，**不另存一份**）。"""
    for _c, q in sites:
        if speak_key(q) == k:
            return q
    return None


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
OTHER_AXES = ("tree", "expect_corpus", "expect_judge", "expect_tree", "expect_flags",
              "speaker", "expect_speaker")
# ★ **探针豁免**：② 那格会给每个 `OTHER_AXES` 项塞一个"不影响数"的探针值，再要求
#   `合计` 逐位不动。以下两项**不能被那样测**，理由各异，所以**按 dest 点名豁免**：
#     · `tree`    （--commit）换对象 = 换一次测量，不是旋钮（原来的豁免，见 ② 的 docstring）
#     · `speaker` （--speaker）**同一族**：换一份旁档 = 换一次测量。它连"换个值数该不该动"
#       都问不出来 —— 探针值（另一个不存在的路径）会让器 exit=11 **不出数**，
#       而 ② 判的正是"出数且合计不动" ⇒ 拿它当探针只会得一个假红。
#   ★ 不许把它们塞进"不许动"那一堆：混进去 = 自测自己调自己，与 `MODE_AXES` 同一类错。
#   ★ 值是**理由**（不是 `True`）：豁免必须在屏幕上说出自己为什么被豁免 ——
#     一个不说理由的豁免，下一个人分不出"它不该测"和"我忘了测"。
PROBE_EXEMPT = {
    "tree": "换对象 = 换一次测量，不是旋钮",
    "speaker": "换旁档 = 换一次测量；探针值只会让器 exit=11 **不出数**，"
               "而这格判的正是「出数且合计不动」⇒ 拿它当探针只会得一个假红",
    "expect_speaker": "它的『正确值』**就是旁档的指纹**，而基线那条命令压根没有旁档 "
                      "⇒ 挑不出探针值。它的门在 ⑤ 里**单独喂**（红7 指纹），不在这儿重复一遍",
}
# ★ **模式开关**：它既不进数、也不是"换一档看数动没动"的旋钮（它连量都不量）——
#   所以**单独点名**，不许塞进 `OTHER_AXES`：自测会拿 `OTHER_AXES` 逐项当"探针"跑一遍，
#   混进去 ⇒ 自测自己调自己（`--selfcheck-gate` 递归）。这与对象轴 `--commit` 是**同一类豁免**：
#   **点名豁免，不混进"不许动"那一堆**（照 `card-c9b12e05-1a0` 那条：豁免要按 dest 点名）。
MODE_AXES = ("selfcheck_gate",)
AXIS_FLAG = {"min_len": "--min-len", "face": "--face", "dedup": "--dedup",
             "v1ref": "--v1ref", "unit": "--unit", "ladder": "--ladder",
             "tree": "--commit", "expect_corpus": "--expect-corpus",
             "expect_judge": "--expect-judge", "expect_tree": "--expect-tree",
             "expect_flags": "--expect-flags", "selfcheck_gate": "--selfcheck-gate",
             "speaker": "--speaker", "expect_speaker": "--expect-speaker"}


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
    # ★★ 旁档（说话人判词）—— 第四个输入，**不是**计数轴：它不改数，它**归类**数。
    #   换一份旁档 = 换一次测量（同 `--commit`），所以进 `OTHER_AXES` 并点名豁免探针。
    ap.add_argument("--speaker", default=None, metavar="<tsv>",
                    help="说话人旁档（TSV）。不变量：**每一行都必须联上器数出来的一条**"
                         "（悬空的判词是错，不是「未判」）；没判到的条进「未判」。"
                         "★ 联结键 = `sha1(引文原文 utf-8)` 前 16 位。")
    #   ★ 指纹分两把，**只有一把是门**（@nova-8980 15:3x 合成的仓规：凡当门用的指纹，
    #     必须指名它的定义域）：
    #       语义指纹（门）  对**排序后的 `(key_sha1, 判词)` 对**算 ⇒ 加注释栏、调列序都不动
    #       字节 sha（对角） `sha256(文件)` ⇒ **加一栏就会变**，只能用来对"我读的是不是同一份文件"
    ap.add_argument("--expect-speaker", default=None, metavar="<语义指纹前16位>",
                    help="旁档的**语义指纹**（`(key_sha1, 判词)` 对）对不上就 exit=11。"
                         "不给 ⇒ 那行自报「★ 没核」。★ 不是文件 sha256 —— 见 `--speaker` 的注。")
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


def _not_empty(abase, base_opts, d, v):
    """探针**是不是空推**：挑好的值 `v` 塞进去之后，那个轴的**生效值**有没有真的变。

    ★ 变了 ⇒ 返回 `v`；没变（或解析不了）⇒ 返回 `None`，由调用方印成「**没测**」。
      「空推」报出来的"没变"与"这个旗标真的不影响数"在屏幕上**一模一样**，而这一格存在的
      全部理由就是「登记错 ⇒ 必须红」—— 探针得先证明自己**推得动**。
    """
    if abase is None:
        return None
    try:
        a2 = build_parser().parse_args(list(base_opts) + [AXIS_FLAG[d], v])
    except SystemExit:
        return None
    return v if str(getattr(a2, d)) != str(getattr(abase, d)) else None


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
#
# ★ 这一格原来叫 `min-len(norm后)` —— **名说它印派生量，它印的是旗标原值**（@nova-8980 现量：
#   1/2/3 三读，印的就是 1/2/3，不是归一化后的长度）。轴本身是单射的，坏的是名。
#   改名**两处必须同一笔**（这里 + 下面印 `量法` 的那行 printf）：只改一处 ⇒ 字段名对不上
#   ⇒ `_fields` 那条检查**静默失效**（`_fields` 的 docstring 自己写的就是这个病）。
#   为什么改成旗标名而不是"真印派生量"：印原值没有信息损失；印派生量是**多一个能撒谎的数**，
#   而"min-len 是按 norm 后的长度截的"这半句已经在 `--min-len` 的说明里写死了。
MEASURE_KEY = {"tree": "commit", "min_len": "min-len", "face": "face",
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


def _run_out(argv):
    """跑一遍、**连 stdout 一起还回来** —— 给"那一行**印了什么**"这类判据用。

    ★ `_run_once` 只还数字与坐标行；而 ⑤ 那些门的判据里有一条是「等式核那一行必须印『成立』」，
      拿不到 stdout 就只能核 rc ⇒ 又回到"只看动了没有"。
    """
    r = subprocess.run([sys.executable, __file__] + argv, capture_output=True, text=True)
    return r.returncode, r.stdout


def _probe_face(rc, tot, tot0, dif, own=None):
    """② 那格的**病名** —— 抽成纯函数**只为一件事：让它能喂红**（见 `selfcheck_gate` ⑤e）。

    ★ 原来的写法把病名和"没出数"混在一起判，于是 @nova-8980 15:4x 复现出一条**红对了、名字错了**
      的判词：探针那一跑 **`tot is None`**（数根本没印出来），而打印走了 `tot != tot0`
      ⇒ 印「数动了 ⇒ 登记错」。**登记本来是对的**，下一个读的人会去改登记。
      ⇒ 「红对了」不等于「判对了」：病名指错方向时，红会**把人送到错的地方去**（比没红更坏）。
    ★ **四**张脸，四种修法：**没出数** / 数动了 / 本轴自己恒等 / 坐标动了（碰了别的轴）。
    ★★ 第四张脸（`own`）是 @nova-8980 补的，缺了它会把**登记错**印成**不止碰一根轴**：
         基点 `unit=all` 时 `ladder` **恒等** ⇒ 数**不动**、而坐标差恰是 `[ladder]`。
       ⇒ 「数动」不是"登记错"的**唯一**形状。判据是：**坐标差里出现本轴以外的东西**才叫
         "不止碰一根轴"；差的那一处**恰是本轴**（`MEASURE_KEY[d]`）⇒ 就是**登记错**，
         副句（坐标差只那一处）是证据，不是罪名。`own=None`（没传）保持旧行为。
    """
    if tot is None:
        return "判不了：探针那一跑**没出数**（rc=%d）⇒ 这格**没测**" % rc
    if tot != tot0:
        return "数动了 ⇒ 登记错"
    if dif is None:
        return "判不了 ⇒ 先修抽行/探针（**没测**）"
    if own is not None and len(dif) == 1 and dif[0] == own:
        return "登记错（数没动，但坐标差的那一处**就是本轴自己**）"
    return "坐标动了 ⇒ 这个探针不止碰一根轴"


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
    dropped = []
    for d in tuple(x for x in OTHER_AXES if x != "tree"):
        if any(t == AXIS_FLAG[d] or t.startswith(AXIS_FLAG[d] + "=") for t in base):
            dropped.append(AXIS_FLAG[d])
        base = _strip_flag(base, AXIS_FLAG[d])
    # ★★ 基点那条命令**要印出来**（@nova-8980 逮的静默替换）：给 `unit` 换登记之后，基点被摘成
    #   `unit=all` ⇒ 屏幕上印的是 `594/520`，而调用方敲的那条命令给的是 `331/302` ——
    #   **两个数一张脸**，没有任何一行说"我摘过什么"。
    #   判据：基线的数与"你敲的那条命令"的数**不是同一个数**时，屏幕上必须看得出来。
    print("   基点命令 = python3 tools/quotes_recount.py %s" % " ".join(base))
    print("   已摘（调用方写了、基点里没有）：%s"
          % (", ".join(dropped) if dropped else "（无）"))
    # ★★ @nova-8980 16:0x 逮的第二刀：**这行原来只说"摘了什么"，没说"换上了什么"**。
    #   实测：同一串**坏**期望值，不带门 `rc=3`、带门 `rc=0` —— 因为门把调用方写的值摘掉、
    #   用**自己现算**的值重加了一遍。⇒ 「门 N 道 · 红 0 · exit=0」这句话里，
    #   **没有一格**在核调用方写的那个值 ⇒ 那是**超额声明**，不是措辞问题。
    #   ⇒ 补两句：① 调用方那份**没参与判定**；② 替换值**逐条印出来**（下面 `good` 算完就印）。
    print("   ★ ★ ① 那四道门**不用调用方写的值**：每一跑都由门**现算**一个值再加回去 ⇒ "
          "调用方写的那份**没参与判定**（「已摘」那行只是「你写过什么」的存档）")
    # ★★ 探针值必须**对着基点那条命令的生效值**挑，且挑完**当场核它真的不一样**。
    #   实测（本卡，@nova-8980）：`unit` 一旦登记进 `OTHER_AXES` ⇒ 基点被摘成 `unit=all`，
    #   而 `_alt_value` 还照**调用方**的 `gone` 去挑 ⇒ 挑出 `all` ⇒ **探针与基点同一个生效值**
    #   ⇒ 空推 ⇒ 那一格印 ✓；红却落在 ③ 的 `ladder`（一个与变异无关的行）——
    #   **一次与原因无关的红，和一次假绿是同一件事的两面。**
    #   ⇒ 两道：① 按**基点**的生效值挑；② 挑完核「探针生效值 ≠ 基点生效值」，相等 ⇒ **没测**（红）。
    #   ★ 空推报出来的"没变"，与"这个旗标真的不影响数"在屏幕上**一模一样**（@iris-64a1 同族：
    #     判不了 ≠ 相同）。
    try:
        abase = build_parser().parse_args(base)
    except SystemExit:
        abase = None                      # 基点自己解析不了 ⇒ 下面的探针一律"没测"
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
    # ★ 替换值**逐条印出来**（@nova-8980 的第二句）。放在这儿是因为 `good` 到这一步才算得出来
    #   —— 而"算不出来"本身要说出来（`None` ⇒ 印「**挑不出**」，不许印成空、更不许省略这一行）。
    #   ★ 只列**① 真正会用的那四道**：多列一格就是又一处"看起来核过"。
    print("   ★ ① 本次的替换值（门现算 —— 这四个才参与判定）：")
    for d in ("expect_corpus", "expect_judge", "expect_tree", "expect_flags"):
        print("       %-15s %s" % (AXIS_FLAG[d], good.get(d) or "★ **挑不出**"))
    print("         ⇒ 判据：**调用方写的那份没参与 ①** ⇒ 「门 N 道全响」这句话"
          "**不能**读成「我钉的语料/判据/树/旗标被核过了」。")

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
    for d in PROBE_EXEMPT:
        print("   ★ 点名豁免 `%s`（%s）" % (d, PROBE_EXEMPT[d]))
    print("   ★ 坐标行 = 器自己印的 量法/对象/语料/判据 四行；**差哪一处都要点名**"
          "（只核「动了没有」的话，「动两根」和「动一根」同签名 —— @iris-64a1 抓的）")
    for d in OTHER_AXES:
        if d in PROBE_EXEMPT:
            continue
        act = acts.get(d)
        v = good.get(d)
        why_none = ""
        if v is None and act is not None:
            v = _alt_value(act, getattr(abase, d, None) if abase else None)
            if v is None:
                why_none = "挑不出探针值"
            elif _not_empty(abase, base, d, v) is None:
                why_none = "挑出来的 %s 与基点**同一个生效值** ⇒ 空推" % v
                v = None
        if v is None:
            print("   %-15s ★ %s ⇒ **没测**（记一笔）" % (d, why_none or "没测"))
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
                 "✓" if ok else "✗ **%s**" % _probe_face(rc, tot, tot0, dif, MEASURE_KEY[d])))

    print("\n③ 计数轴（门：印出的旗标行必须动 · 提示：数动没动**不判红**）")
    ax_moved = ax_same = 0
    for d in COUNT_AXES:
        act = acts.get(d)
        v = _alt_value(act, getattr(abase, d, None) if abase else None) \
            if act is not None else None
        why_none = "挑不出第二值"
        if v is not None and _not_empty(abase, base, d, v) is None:
            why_none = "挑出来的 %s 与基点**同一个生效值** ⇒ 空推" % v
            v = None
        if v is None:
            print("   %-15s ★ %s ⇒ **没测**（记一笔）" % (d, why_none))
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
            alt = _alt_base(base, (getattr(abase, "unit", None) if abase else None)
                            or getattr(a, "unit", None) or "all")
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

    # ── ⑤ 旁档读入侧（`card-5fd27a3a-aab`）：**每条门各喂一次红** ───────────────────
    #   ★ 为什么要有这一块：④ 那一课说得很清楚 ——「刚落这条修法的人，最容易在新那一层复犯旧病」。
    #     读入侧一口气加了 7 张脸（悬空/表头/值域/重复键/空表/分母/对象），
    #     若只印出来、不各喂一次红，那 7 张脸本身就成了**一批新的"不可能失败的门"**。
    #   ★ 旁档从**器自己数出来的条**造（⇒ 联结按构造成立），再逐格改坏：
    #     这样"正臂绿"与"红臂红"的**唯一差**就是那一处故意的改动，没有别的变量。
    print("\n⑤ 旁档读入侧（门：正臂必须出数 · 每条门各喂一次红 ⇒ rc=11 **且脸要对**）")
    ba = build_parser().parse_args(base)
    bd = tree_dir(ba.tree)
    try:
        ba.corpus = V.Corpus(docs, V.norm) if ba.unit == "gone" else None
        bsites = list(_sites(bd or V.ROOT, ba))
    finally:
        if bd:
            shutil.rmtree(bd, ignore_errors=True)
    bper = _per_quote(bsites)
    bface = _face_of(bper)
    bq = dict((speak_key(q), q) for q in bper)
    bkeys = sorted(bq)[:3]

    def _mk(path, rows, hdr=True, denom=None, tree=None):
        """造一份旁档 —— ★ 它**不是**任何一次真读数，所以行里那几栏故意写「自测」。"""
        L = ["# 自测造的旁档（不是任何一次真读数；对象/分母都由自测按需塞进去）"]
        if tree:
            L.append("# tree %s" % tree)
        if denom:
            L.append("# 分母：%d 处 / %d 条" % denom)
        if hdr:
            L.append("# columns\t" + "\t".join(
                ["面", "引文", "判词", "坐标", "判据", "key_sha1"]))
        for k, v in rows:
            # ★ `bq.get`：红1 那一行**故意**是个联不上的键 ⇒ 显示栏只能空着
            #   （第一版用 `bq[k]`，自测自己在造红那一行时先崩了 —— KeyError）。
            q = bq.get(k, "")
            L.append("\t".join([bface.get(q, "代码面"),
                                _cut(q.replace("\n", "⏎").replace("\t", " "), 30),
                                v, "自测", "自测", k]))
        open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")

    spdir = tempfile.mkdtemp(prefix="speakself")
    try:
        good_rows = [(bkeys[0], "a"), (bkeys[1], "省略"), (bkeys[2], "b")]
        pp = os.path.join(spdir, "ok.tsv")
        _mk(pp, good_rows)
        rec, err = load_speaker(pp, bsites)
        if err is not None:
            print("   %-14s ★ 自测自己造的旁档都读不进来（脸=%s）⇒ **没测**（记一笔）"
                  % ("正臂", err[0]))
            gates += 1
            red += 1
        else:
            rc, out = _run_out(base + ["--speaker", pp, "--expect-speaker", rec["fp_sem"]])
            # ★ 判据的两侧都**不许靠加粗**：原来写成 `⇒ **成立**`，另一面写成 `⇒ **不成立**`，
            #   而"抽不到"与"不成立"共用一张脸 ⇒ 正臂那一格自己先假红。
            #   ⇒ 正则里 `**` 当**可选**，判词按**字**取。
            m = re.search(r"等式核（[^\n]*⇒ \*{0,2}(成立|不成立（器自己坏了）)", out)
            ok = (rc == 0 and m is not None and m.group(1) == "成立")
            gates += 1
            red += 0 if ok else 1
            print("   %-14s rc=%d · 等式核 %s ⇒ %s"
                  % ("正臂（3 条全联上）", rc, (m.group(1) if m else "**没印出来**"),
                     "✓" if ok else "✗ **旁档进来了却出不了数/等式不成立**"))
            for lab, kw in (
                    ("红1 悬空", dict(rows=[(bkeys[0], "a"),
                                            (bkeys[1][:-1] + ("0" if bkeys[1][-1] != "0" else "1"), "省略")])),
                    ("红2 表头", dict(rows=good_rows, hdr=False)),
                    ("红3 未声明的值", dict(rows=[(bkeys[0], "c"), (bkeys[1], "省略")])),
                    ("红4 重复键", dict(rows=[(bkeys[0], "a"), (bkeys[0], "b")])),
                    ("红5 分母对不上", dict(rows=good_rows, denom=(1, 1))),
                    ("红6 对象对不上", dict(rows=good_rows, tree="0" * 40))):
                want = lab.split()[-1]
                q = os.path.join(spdir, "r.tsv")
                _mk(q, kw.pop("rows"), **kw)
                rc, out = _run_out(base + ["--speaker", q])
                got = re.search(r"脸 = (\S+)", out)
                ok = (rc == 11 and got is not None and got.group(1) == want)
                gates += 1
                red += 0 if ok else 1
                print("   %-14s rc=%d（要 11）· 脸 = %s（要 %s）⇒ %s"
                      % (lab, rc, got.group(1) if got else "**没印**", want,
                         "✓" if ok else "✗ **这扇门没响，或响错了名字**"))
            # 红7 指纹：唯一一道**不在文件里**的门（`--expect-speaker` 比的是器算的语义指纹）
            q = os.path.join(spdir, "f.tsv")
            _mk(q, good_rows)
            bad = rec["fp_sem"][:-1] + ("0" if rec["fp_sem"][-1] != "0" else "1")
            rc, out = _run_out(base + ["--speaker", q, "--expect-speaker", bad])
            got = re.search(r"脸 = (\S+)", out)
            ok = (rc == 11 and got is not None and got.group(1) == "指纹")
            gates += 1
            red += 0 if ok else 1
            print("   %-14s rc=%d（要 11）· 脸 = %s（要 指纹）⇒ %s"
                  % ("红7 指纹", rc, got.group(1) if got else "**没印**", "✓" if ok else "✗ **没响**"))
    finally:
        shutil.rmtree(spdir, ignore_errors=True)

    # ⑤e ★ 喂一口**"探针那一跑没出数"**（@nova-8980 15:4x 复现的那口）：
    #   病名必须落在「**没出数**」上，**不许**落在「数动了 ⇒ 登记错」上 ——
    #   后者会让下一个读的人去改**本来是对的**登记（红对了、判错了，比没红更坏）。
    #   ★ 这里**不重跑子进程去凑**那个局面（那是寻绿）：直接拿已知输入喂纯函数。
    f_totnone = _probe_face(6, None, "331/302", None)
    ok = ("没出数" in f_totnone and "登记错" not in f_totnone)
    gates += 1
    red += 0 if ok else 1
    print("   ⑤e           探针跑 rc=6 且 tot=None ⇒ 判词「%s」⇒ %s"
          % (_cut(f_totnone, 46), "✓" if ok else "✗ **病名点回「登记错」了**"))

    # ⑤f ★ 同一张脸的另一半（@nova-8980 补的第四张脸）：
    #   数**没动**、坐标差**恰是本轴自己** ⇒ 病名必须是**登记错**，不许是「不止碰一根轴」。
    #   现场（@atlas-791f 读数）：基点 `unit=all` 时 `ladder` 恒等。
    #   ★ ⑤e 与 ⑤f 合起来钉住的正是那条被写窄的判据：**"数动"不是"登记错"的唯一形状。**
    f_own = _probe_face(0, "331/302", "331/302", ["ladder"], "ladder")
    ok = ("登记错" in f_own and "不止碰一根轴" not in f_own)
    gates += 1
    red += 0 if ok else 1
    print("   ⑤f           数没动 · 坐标差恰是本轴(ladder) ⇒ 判词「%s」⇒ %s"
          % (_cut(f_own, 42), "✓" if ok else "✗ **把登记错印成「不止碰一根轴」了**"))

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
        print("量法   口径参数：commit=%s · unit=%s · min-len=%d · face=%s · "
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
        # ★ 落点**扫一次**：合计与说话人轴的分母出自同一份（漂了没人红 = 两份手写声明的病）
        sites = list(_sites(base, a))
        # ★★ 旁档**读在印数之前**：读不成 ⇒ exit=11，**一个数都不许印出来**。
        #   （放在 per-cell 表之后就成了「拒绝出数」的空话 —— 数已经印了。）
        sp = None
        if a.expect_speaker is not None and a.speaker is None:
            print("★ `--expect-speaker` 给了、却没给 `--speaker` ⇒ **拒绝出数**（exit=11）。")
            print("  这道门没有可比的对象 —— 「看起来验过」与「验过」的区别正是这一格。")
            return 11
        if a.speaker is not None:
            sp, err = load_speaker(a.speaker, sites)
            if err is not None:
                print("★ 旁档这一格**拒绝出数**（exit=11）。脸 = %s" % err[0])
                for w in err[1]:
                    print("   %s" % w)
                return 11
            per_now = _per_quote(sites)
            if sp["decl_tree"] and got_tree and sp["decl_tree"] != got_tree:
                print("★ 旁档与本次跑的**对象**对不上 ⇒ **拒绝出数**（exit=11）。脸 = 对象对不上")
                print("  旁档自己声明（`# tree` 那行）  %s" % sp["decl_tree"])
                print("  本次跑解析出来的对象            %s" % got_tree)
                print("  ★ 旁档的判词是**对某一棵树的某一处**作的判 —— 换树必须重判，"
                      "拿旧树的判词配新树的处就是把两个对象当一个用。")
                return 11
            if a.expect_speaker is not None and sp["fp_sem"] != a.expect_speaker:
                print("★ 旁档的**语义指纹**对不上 ⇒ **拒绝出数**（exit=11）。脸 = 指纹")
                print("  期望 --expect-speaker %s" % a.expect_speaker)
                print("  实际（对排序后的 `(key_sha1, 判词)` 对算）  %s" % sp["fp_sem"])
                print("  ★ 门装在**语义指纹**上，不是文件 sha256：@iris-64a1 今天给旁档加了一行"
                      "`# columns` 机器可读表头，**一个判词都没改**，文件 sha(65fc…→67072a40…) 就变了。")
                print("    字节 sha 是「**文件长相**」的函数 —— 它只能答「我读的是不是同一份文件」"
                      "（所以我在旁档那行把文件名跟它印在一起），**不能当门**。")
                return 11
        rows, tot = tally(base, a, sites)
        if sp is not None and sp["decl_denom"] and sp["decl_denom"] != (tot[0], len(_per_quote(sites))):
            print("★ 旁档与本次跑的**分母**对不上 ⇒ **拒绝出数**（exit=11）。脸 = 分母对不上")
            print("  旁档自己声明（`# 分母：` 那行）  %d 处 / %d 条" % sp["decl_denom"])
            print("  本次跑现场算出来的            %d 处 / %d 条（全局去重 raw）"
                  % (tot[0], len(_per_quote(sites))))
            print("  ★ 这一格是「**同一份旁档配了另一套旗标**」的专用出口："
                  "旁档那一行自己写着「当场算、当场印，非写死」⇒ 它是坐标，不是注释。")
            print("    例：`--face literal` / 换 `--ladder` / 换 `--min-len` 都会挪分母，"
                  "而旁档的行数**一行不变** —— 那时逐行联结照样全中，只有这一格拦得住。")
            return 11
        for name, n, k in rows:
            print("  %-8s %4d 处 / %4d 条" % (name, n, k))
        print("  %-8s %4d 处 / %4d 条" % ("合计", tot[0], tot[1]))
        print()
        speaker_axis(sites, tot, a, sp)
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
