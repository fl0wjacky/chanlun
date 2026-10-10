#!/usr/bin/env python3
"""前端里凡是读**原始线段**（载荷的 `segs`）的地方，都得写明为什么不读图上画的那套（`segs_std`）。

来历：小栋 10-10 05:18 问「为什么会出现两套线段标准的问题？」（card-83915c20-9e3）。D-3 C 以后图上画的是
标准化线段 `segs_std`，可前端好几处还在读原始 `segs`：框的左右边（线上 222 个框里 60 个画错）、状态栏「完成线段 N」、
「看得见的变化」签名、boxSplit 的拆点……每一处都是「图上画的是 A、算的是 B」。

规矩：`web/*.js` 里每一处 `.segs`（属性读取，不含 `segs_std`）所在的那一行或**上一行**，必须带一个
`RAW-SEGS:` 注释，写明理由（典型：未完成段／暂定段只在原始里有；老后台没有 segs_std 时的退路；体检两套都查）。
没写理由的读法 ⇒ 红。新加一处读原始线段，就得在这里当面说清楚为什么。

  python3 tools/web_std_segs_check.py            # 主跑：列出每一处读法和它的理由，没理由的红
  python3 tools/web_std_segs_check.py --selftest # 探针：①去掉一个理由 ②新加一处没理由的读法，两格都得变红
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["web/app.js", "web/layers.js"]
READ = re.compile(r"\.segs\b(?!_)")          # `.segs`，不含 `.segs_std`
MARK = "RAW-SEGS:"


def scan(texts):
    """texts: {文件名: 全文} → (读法列表, 没理由的列表)。读法 = (文件, 行号, 那一行, 理由所在行)。"""
    reads, bad = [], []
    for fn, text in texts.items():
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            code = ln.split("//")[0]
            if not READ.search(code):
                continue
            why = ln if MARK in ln else (lines[i - 1] if i and MARK in lines[i - 1] else None)
            reads.append((fn, i + 1, ln.strip(), why))
            if why is None:
                bad.append((fn, i + 1, ln.strip()))
    return reads, bad


def load():
    return {fn: open(os.path.join(ROOT, fn), encoding="utf-8").read() for fn in FILES}


def main():
    reads, bad = scan(load())
    for fn, n, ln, why in reads:
        tag = "✓" if why else "✗"
        reason = why.split(MARK, 1)[1].strip() if why else "（没写理由）"
        print(f"  {tag} {fn}:{n}  {ln[:90]}\n       理由：{reason[:90]}")
    if not reads:
        print("✗ 一处 `.segs` 读法都没扫到 —— 尺子自己可能坏了（前端不可能完全不读原始线段：未完成段只在那里有）")
        return 1
    if bad:
        print(f"✗ {len(bad)} 处读原始线段没写理由（共 {len(reads)} 处）：要么换成 segs_std，要么在那一行或上一行写 `// {MARK} …`")
        return 1
    print(f"✓ 前端读原始线段 {len(reads)} 处，每一处都写明了为什么不读 segs_std")
    return 0


def selftest():
    base = load()
    ok = []
    # ① 去掉第一个理由 ⇒ 至少多出一处没理由的读法
    fn = next(f for f in FILES if MARK in base[f])
    t1 = dict(base); t1[fn] = base[fn].replace(MARK, "RAW_SEGS_REMOVED", 1)
    ok.append(("去掉一处理由", bool(scan(t1)[1])))
    # ② 新加一处没理由的读法（状态栏数线段那种）⇒ 红
    t2 = dict(base); t2["web/app.js"] = base["web/app.js"] + "\nconst probe = d.segs.length;\n"
    ok.append(("新加一处没理由的读法", any("probe" in b[2] for b in scan(t2)[1])))
    # ③ `segs_std` 不算读原始（别把正确的换法也拦下来）
    t3 = dict(base); t3["web/app.js"] = base["web/app.js"] + "\nconst probe2 = d.segs_std.length;\n"
    ok.append(("segs_std 不误报", not any("probe2" in b[2] for b in scan(t3)[1])))
    for name, good in ok:
        print(("✓ " if good else "✗ ") + name)
    n = sum(g for _, g in ok)
    print(("✓" if n == len(ok) else "✗") + f" 自检：{n}/{len(ok)} 格探针都对")
    return 0 if n == len(ok) else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
