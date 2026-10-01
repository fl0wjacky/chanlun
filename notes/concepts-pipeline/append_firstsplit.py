# -*- coding: utf-8 -*-
"""按 @nova-8980 2026-10-01 06:07 的口径，给「首次出现」那一列出一张**补丁表**（只加不改）。

口径原文（nova）：
    「首见拆成两栏，**『说法首见』**和**『内容首见』**。两处是同一课就只写一栏；
      只在预告里出现、正文没兑现的，『内容首见』写『原文未给』。」

★ 为什么走「补丁表」而不是改正文那一列：
  正文那列已经被小栋／nova／atlas 引过，**改列会让此前引过的人手上的坐标失效**；
  补丁表能同时留着旧坐标和拆栏后的新坐标，且不碰冻结的正文（只加不改）。

★ 两栏怎么来的（都可复算，不是手填）：
  · **说法首见** = 词形首见。`first.py` 机械扫出来的那一档（按课号从小到大，
    概念名 ＋ 别名栏一起搜，逐字子串）。
  · **内容首见** = 本表正文『首次出现（课号）』那一列 —— 就是**已按技术义校过**的那个数。
  ⇒ 于是「需要拆栏的行」＝ `first.py` 报『表上更晚』的那一批：**机械首见比表上早**
     ＝ 词形先出现过、但当时还不是这个意思 ⇒ 两栏天然不同。
  ⇒ 报『一致』的行 ＝ 两处同课 ⇒ 照 nova 的口径**只写一栏**。

用法（任意 CWD）：python3 notes/concepts-pipeline/append_firstsplit.py [--dry]
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, "docs/concepts/inventory_中枢走势组.md")
FIRST = os.path.join(ROOT, "notes/concepts-pipeline/first.py")

# ★ 逐行判据（人写）：为什么机械首见那一课不是「内容首见」。
#   键必须与 first.py 报出来的名字**逐字对上**，对不上就炸 —— 防止口径悄悄漂走。
WHY = {
    "走势": "L2 那处是日常义（讲市场规则），到 L7 才当**技术义**泛指；L7 即内容首见",
    "上涨 / 下跌": "机械命中的是 **L3 的「上涨」**（日常义）。表上把首见记在 L15 —— 那里才**给出判据**（高高低低）；L17 再换成中枢判据",
    "盘整": "L7 的「盘整」是日常义；L15 才给判据（与上涨/下跌同一条）",
    "趋势": "机械命中的是 **L3 的「上涨」**（趋势按方向二分，别名带进来的）。L16:3 才第一次把「上涨、下跌」合称趋势，**正式定义在 L17**",
    "中枢延伸 / 延续": "机械命中的是 **L7 的「延续」**（普通动词义）。L20:15 才把小标题写成「中枢延伸」，**内容首见 L20**",
    "中枢扩展 / 扩张": "机械命中的是 **L10 的「扩张」**（不是中枢的扩张）。L20:2 标题里的「级别扩张」是首次把它挂到中枢上，**正文讲在 L21:40**",
    "级别": "机械 L1 命中「级别」，但表上 L15:18-19 才第一次把它当**走势的属性**用（该句原文有重复字）。L1 那处不是本义",
    "最低级别": "机械 L17 是**定义中枢时**顺带提的；L19:83「一字线构成的就是最低级别的价值中枢」才正面给出取法，L29／L35 正式化",
    "结合律": "机械命中的是 **L18 的「结合性」**（写法不同、且是在 K 线包含关系里提的）。L24:157 才有「结合律」这个词形，**引入在 L35**",
    "走势类型延伸": "机械命中的是 **L15 的「延伸」**（泛指）。L18 才把它做成概念（走势类型延伸）",
    "【跨组】第三类买卖点定理": "机械命中的是 **L14 的「三买」**（口语简写）。L20 才有「第三类买卖点定理」这个说法。**该行归动力学组**",
}

# ★ nova 口径里的特例：**只在预告里出现、正文没兑现的** ⇒ 内容首见写『原文未给』。
UNFULFILLED = {
    "趋势的方向（中枢的方向）":
        "全库**两处提问、零处定义**：L25:178-179 逐字问「其中并没有定义中枢的方向」，"
        "答（L25:182-183）只答了提问的后半（一路涨停的股票）；L17:350-351 又问一次"
        "（用词「向上或向下中枢」），答（L17:352）「明白就好」。⇒ **正文始终没兑现**",
}


def run_first():
    """跑 first.py，取三档的名单 —— 单一真源，不在本脚本里重写一遍扫描。"""
    out = subprocess.run([sys.executable, FIRST], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    same, late = [], []
    for line in out.split("\n"):
        line = line.strip()
        if not line.startswith("|" * 0):
            pass
        m = re.match(r"^(?:★\s*)?(.+?)\s*\|\s*(.*?)\s*\|\s*(L\d+（[^）]*）|—)\s*\|\s*(.+)$", line)
        if not m:
            continue
        name, declared, mech, verdict = m.group(1).strip(), m.group(2), m.group(3), m.group(4).strip()
        if verdict == "一致":
            same.append((name, declared, mech))
        elif verdict.startswith("表上更晚"):
            late.append((name, declared, mech))
    assert same and late, "first.py 输出没解析到 —— 它的表头格式变了？"
    return same, late


def main():
    same, late = run_first()
    names = {n for n, _, _ in late}
    missing = names - set(WHY)
    extra = set(WHY) - names
    assert not missing, "first.py 报的「表上更晚」里这几行我没有判据，别硬写：%s" % sorted(missing)
    assert not extra, "WHY 里这几行已经不在「表上更晚」里了（口径漂了，重看一眼）：%s" % sorted(extra)

    b = []
    def p(s=""):
        b.append(s)

    p("## 附录十三：首次出现拆栏补丁（『说法首见』／『内容首见』）")
    p()
    p("**只加不改**：正文『首次出现（课号）』那一列**一个字没动** —— 它已被小栋／nova／atlas 引过，"
      "改列会让此前引过的人手上的坐标失效。本附录是**并行的补丁表**，同一件事两套坐标都给。")
    p()
    p("- **口径（@nova-8980 2026-10-01 06:07）**：首见拆两栏 —— **『说法首见』**（这个**词形**最早出现在哪一课）"
      "与**『内容首见』**（这件事**第一次被讲到位**是哪一课）。**两处同课就只写一栏**；"
      "只在预告里出现、正文没兑现的，『内容首见』写『原文未给』。")
    p("- **两栏怎么算的（都可复算）**：『说法首见』＝ `notes/concepts-pipeline/first.py` 机械扫出来的词形首见"
      "（按课号从小到大、概念名＋别名一起搜、逐字子串）；『内容首见』＝ 正文那一列（已按技术义校过）。"
      "⇒ **需要拆栏的，就是 `first.py` 报『表上更晚』的那批** —— 机械首见更早，说明那时词形到了、意思还没到。")
    p("- 旧档读数：`first.py` 一致 **%d** ｜ 表上更晚 **%d** ｜ ★真错 **0**。" % (len(same), len(late)))
    p()
    p("| 概念 | 『说法首见』（词形首见，机器扫） | 『内容首见』（第一次讲到位） | 差在哪 |")
    p("|---|---|---|---|")
    for name, declared, mech in late:
        p("| **%s** | %s | %s | %s |" % (name, mech, declared.replace("|", "／"), WHY[name]))
    for name, why in UNFULFILLED.items():
        p("| **%s** | — | **『原文未给』** | %s |" % (name, why))
    p()
    # ★ 已在上面单列的行（如『趋势的方向』—— 脚本一个字都搜不到）不算「同课」，
    #   否则同一行在两处出现，读的人会以为它既没兑现又同课。
    rest = [n for n, _, _ in same if n not in UNFULFILLED]
    p("**其余 %d 行：两栏同课，照口径只写一栏** —— 正文那一列的课号同时就是『说法首见』和『内容首见』："
      % len(rest))
    p()
    p("　" + " ｜ ".join(re.sub(r"\*+$", "", n) for n in rest))
    p()
    p("★ 本表**不替代**正文那一列，也不改它；引用时若要说『第一次讲到位』，请引**『内容首见』**这一栏。")

    old = open(P, encoding="utf-8").read()
    if "--dry" in sys.argv:
        print("\n".join(b))
        print("\n--dry：未写盘（%d 行）。" % len(b))
        return 0
    assert "## 附录十三" not in old, "附录十三 已存在，别重复追加"
    open(P, "w", encoding="utf-8").write(old.rstrip("\n") + "\n\n" + "\n".join(b).rstrip("\n") + "\n")
    print("追加完成：%d 行（拆栏 %d 行 ＋ 未兑现 %d 行 ＋ 同课 %d 行）"
          % (len(b), len(late), len(UNFULFILLED), len(same)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
