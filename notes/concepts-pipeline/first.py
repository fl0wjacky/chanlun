# -*- coding: utf-8 -*-
"""「首次出现（课号）」那一列的口径脚本。

★ 为什么有这个文件（2026-10-01）：
  本品前言里写着「首见课号那一列…是**另行按课号从小到大扫每一课**扫出来的（见 `first.py` 那一步）」，
  但 `first.py` **从来没存在过** —— `git ls-files` 没有、`git log --all` 里从未进过任何提交。
  于是那句话没人能复算。这份是**按那句判据重建的**，不是原件。

判据（照前言原话）：
  · 顺序：**按课号从小到大**扫每一课，取**第一课**出现者 —— **不是**从「命中数」推的
    （命中数是全库计数，跟先后无关；二者恰好常相同，但推理链不同）。
  · 搜什么：概念名 ＋ 该行「别名／异写」栏里的别名，**一起搜**（照前言第 3 条的检索口径）。
  · 逐字：把每课先删换行（语料折叠），再 `in` 判子串 —— 与 finalcheck/checkquotes 同一把尺。
  · **技术义由人判**：脚本给的是**机械首见**；非技术义的假命中由人点掉、写进备注
    （例：『走势』机械首见 L3，但那是「所有走势都受法律保护」的日常义，表上记 L7）。

输出三档，**只报差异，不替人裁**：
  · 一致        —— 表上写的首见课号 ＝ 机械首见
  · 表上更晚    —— 表上更晚，**必须在备注里有非技术义的解释**（否则是漏了备注）
  · ★表上更早   —— 表上写了一个**比最早逐字出现还早**的课 ⇒ **不可能**，那是错的（真错档）

用法（在本 worktree 根跑，也可从任意 CWD 跑）：
    python3 notes/concepts-pipeline/first.py
复算前提：`archive/chanlun108/text/` 需与本仓同相对路径就位（`archive/` 未进仓）。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "archive/chanlun108/text")
DOC = os.path.join(ROOT, "docs/concepts/inventory_中枢走势组.md")
assert os.path.isdir(D), "语料不在 %s —— archive/ 未进仓，需与本仓同相对路径就位" % D

# ---- 语料：课号 → 删换行后的正文（与 finalcheck.py 同一把尺）----
CORP = {}
for f in sorted(os.listdir(D)):
    n = int(re.search(r"(\d+)", f).group(1))
    CORP[n] = open(os.path.join(D, f), encoding="utf-8").read().replace("\n", "")
assert len(CORP) == 108, "语料课数 %d ≠ 108" % len(CORP)
LESSONS = sorted(CORP)


def terms(name, alias):
    """概念名 ＋ 别名栏 → 实际要搜的串集合。

    别名栏是给人看的，混着计数（『中枢 2632』）、说明（『（趋势按方向二分）』）、
    分隔（`｜` `/`）、记号（`[ZD，ZG]`）。这里只**机械地**剥掉计数与说明，剩下的当别名。
    """
    # ★ 概念名本身也会带分隔（『上涨 / 下跌』『ZG / ZD』『GG / G / D / DD』）——
    #   只剥别名栏不剥概念名，这四个会「一个都不命中」，那是**脚本的口径缺口，不是表的错**。
    # ★ 概念名与别名走**同一道**过滤。原先只滤别名，结果『GG / G / D / DD』里的单字
    #   `D` 直接成了搜索词、命中 L1，报出「机械首见 L1（D）」这种假信号。
    #   单字符一律不要（`D`/`G` 是噪声）；两个字符的 ASCII 记号要留（`ZD`/`ZG`/`GG`/`DD`/`Zn`）。
    out = {name}
    for piece in re.split(r"[｜|/]", name + "｜" + alias):
        piece = re.sub(r"（[^）]*）", "", piece)           # 去说明
        piece = re.sub(r"\s*\d+\s*$", "", piece).strip()   # 去结尾计数
        piece = piece.strip(" 　`*[]()、，,")
        if not (2 <= len(piece) <= 24) or piece.startswith("—"):
            continue
        out.add(piece)
    return {t for t in out if t}


def first_lesson(t):
    for n in LESSONS:
        if t in CORP[n]:
            return n
    return None


rows, bad = [], []
doc = open(DOC, encoding="utf-8").read()
table = doc[doc.index("| 概念 |"):doc.index("## 附录")]
for line in table.split("\n"):
    if not line.startswith("|") or line.startswith("|---") or line.startswith("| 概念 |"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 3:
        continue
    raw_name, alias, declared = cells[0], cells[1], cells[2]
    name = re.sub(r"^【跨组】", "", raw_name).strip("* ").split("（")[0].strip()
    if not name:
        continue
    ts = terms(name, alias)
    hits = sorted((n, t) for n, t in ((first_lesson(t), t) for t in ts) if n)
    if not hits:
        # ★ 搜不到 ≠ 表错。只有当表上**写了课号**而脚本一个形式都搜不到时，才另记一档
        #   （口径没覆盖到这个概念名），**不进「真错」** —— 否则就是拿脚本的缺口冤枉表。
        if re.search(r"L\d+", declared):
            rows.append((name, declared, "—", "○ 脚本没搜到（口径缺口，非表错）"))
        else:
            rows.append((name, declared or "—", "—", "一致"))
        continue
    mech, which = hits[0]
    d = re.findall(r"L(\d+)", declared)
    verdict = "表上写「—」"
    if d:
        dn = min(int(x) for x in d)
        verdict = "一致" if dn == mech else ("表上更晚（要备注）" if dn > mech else "★表上更早")
        if dn < mech:
            bad.append(name)
    rows.append((name, declared or "—", "L%d（%s）" % (mech, which), verdict))

w = max(len(r[0]) for r in rows)
print("【「首次出现（课号）」复算】共 %d 行\n" % len(rows))
print("%-*s | %-22s | %-22s | %s" % (w, "概念", "表上写的", "机械首见", "判"))
for name, dec, mech, verdict in rows:
    flag = "  " if verdict in ("一致", "表上更晚（要备注）", "表上写「—」") else "★ "
    print("%s%-*s | %-22s | %-22s | %s" % (flag, w, name, dec[:22], mech, verdict))
print()
print("一致 %d ｜ 表上更晚（须有备注解释）%d ｜ ★ 真错 %d ｜ 脚本没搜到（口径缺口）%d"
      % (sum(1 for r in rows if r[3] == "一致"),
         sum(1 for r in rows if r[3] == "表上更晚（要备注）"),
         sum(1 for r in rows if r[3] == "★表上更早"),
         sum(1 for r in rows if r[3].startswith("○"))))
mis = [r for r in rows if r[3] == "表上更晚（要备注）"]
print("\n★『表上更晚』那 %d 行的课号（每行都必须在备注里有非技术义的解释，否则是漏了备注）：" % len(mis))
for r in mis:
    print("   %s：表上 %s ｜ 机械 %s" % (r[0], r[1][:40], r[2]))
