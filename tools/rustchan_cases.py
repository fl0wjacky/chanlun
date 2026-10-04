#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rust-chan 的 53 个线段划分例子（src/tests/forest_tests.rs）→ 我们的 build_segments 逐个对（小栋 10-03 定 ③A）。

    python3 tools/rustchan_cases.py                    # 对一遍，rc=0 才算过（selfcheck 也调 check()）
    python3 tools/rustchan_cases.py --extract <上游 checkout>   # 从上游重新抽例子（先核文件 sha256）

数据在 tools/rustchan/forest_cases.json（离线可跑）；出处、许可证见 tools/rustchan/UPSTREAM.md、LICENSE。
只搬**测试数据**（笔端点值 + 上游期望的段界），不搬上游代码。

每个例子：
  poles            笔端点值（相邻两个就是一笔）
  upstream_state / upstream_segmented   上游断言原样（segmented 里最后一个是没走完的段终点）
  rust_confirmed   上游「已确认段界」= segmented 去掉最后一个（不足 3 个 ⇒ 空），即它 assert 的 forest.indexes()
  ours_confirmed   我们**钉住**的已确认段界（引擎一改就对不上 ⇒ 红，要人看过再重钉）
  verdict          "identical"（与上游逐位相同）或 "caliber"（口径不同，必须带原文出处 cite）

比的只有「已确认段界」；上游的 State 是它自己状态机的名字，我们没有对应物，不比。
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "rustchan", "forest_cases.json")
UPSTREAM_FILE = "src/tests/forest_tests.rs"
UPSTREAM_SHA256 = "a33a10409a57c53c2175de62e50c987cddde09f29ec954198780d540e19751da"   # 上游 1d1cc06 那份
N_CASES = 53

# 口径不同的 7 个：分两类，原文出处逐条回本课核过（lesson-067/071/077/078.txt 行号）
CITE_BACKWARD = [
    "L067:31-33 第二种情况：须从顶分型高点开始的反向序列出现底分型，才在该高点结束",
    "L071:26-28 先破第一笔的开始位置 ⇒ 旧线段只被一笔破坏、依然延续",
    "L078:39-41 没形成第二特征序列的分型又直接新高或新低 ⇒ A、B、C 加起来只算一个线段",
]
CITE_UNCONVERGED = [
    "L067:31-33 第二种情况：须从顶分型高点开始的反向序列出现底分型，才在该高点结束",
    "L078:39-41 没形成第二特征序列的分型又直接新高或新低 ⇒ A、B、C 加起来只算一个线段",
    "L077:71-74 线段必须被线段所破坏才能确定其完成",
]
WHY_BACKWARD = "上游 Forest::backward() 以「反向跌破段起点」终结线段；原文里跌破起点是延续、不是终结"
WHY_UNCONVERGED = "上游在反向序列还没走出底分型（未收敛 / 直接新高）时就切段；原文要线段破坏、要分型"
CALIBER = {n: ("backward", WHY_BACKWARD, CITE_BACKWARD) for n in ("go_124", "go_12214", "go_12224")}
CALIBER.update({n: ("unconverged", WHY_UNCONVERGED, CITE_UNCONVERGED)
                for n in ("go_12311", "go_12321", "go_122114", "go_123124")})

_CASE = re.compile(r"fn\s+(\w+)\(\)\s*\{\s*assert_forest_eq\(State::(\w+),\s*&\[([^\]]*)\],\s*&\[([^\]]*)\]\);", re.S)


def pens_of(poles):
    """笔端点值 → build_segments 吃的笔（下标就是端点序号，跟上游 pole 序号一一对应）。"""
    return [dict(i0=j, i1=j + 1, p0=poles[j], p1=poles[j + 1], hi=max(poles[j], poles[j + 1]),
                 lo=min(poles[j], poles[j + 1])) for j in range(len(poles) - 1)]


def confirmed(segs):
    """已走完的线段两端（端点序号）的集合 —— 对上游 forest.indexes()。"""
    out = set()
    for s in segs:
        if not s.get("live"):
            out |= {s["PI0"], s["PI1"] + 1}
    return sorted(out)


def rust_confirmed(segmented):
    return sorted(set(segmented[:-1])) if len(segmented) >= 3 else []


def load():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def check(build_segments, cases=None):
    """→ 问题列表（空 = 过）。selfcheck 调这个；变异探针换 build_segments / cases 进来。"""
    cases = load()["cases"] if cases is None else cases
    bad = []
    if len(cases) != N_CASES or len({c["name"] for c in cases}) != N_CASES:
        bad.append("例子个数 / 名字不对：%d 个、%d 个不同名（应 %d）"
                   % (len(cases), len({c["name"] for c in cases}), N_CASES))
    for c in cases:
        ours = confirmed(build_segments(pens_of(c["poles"])))
        rust = rust_confirmed(c["upstream_segmented"])
        if rust != c["rust_confirmed"]:
            bad.append("%s 上游期望被改过：%s ≠ %s" % (c["name"], c["rust_confirmed"], rust))
        if ours != c["ours_confirmed"]:
            bad.append("%s 引擎变了：现在 %s，钉住的是 %s" % (c["name"], ours, c["ours_confirmed"]))
        if c["verdict"] == "identical":
            if c["ours_confirmed"] != rust:
                bad.append("%s 标「逐位相同」，可我们 %s ≠ 上游 %s" % (c["name"], c["ours_confirmed"], rust))
        elif c["verdict"] == "caliber":
            if not c.get("cite"):
                bad.append("%s 标「口径不同」却没有原文出处" % c["name"])
            if not set(c["ours_confirmed"]) < set(rust):
                bad.append("%s 标「口径不同」，但不是「我们比上游少切」：%s vs %s"
                           % (c["name"], c["ours_confirmed"], rust))
        else:
            bad.append("%s verdict 不认识：%r" % (c["name"], c["verdict"]))
    return bad


def extract(upstream_dir, build_segments):
    path = os.path.join(upstream_dir, UPSTREAM_FILE)
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != UPSTREAM_SHA256:
        raise SystemExit("上游文件 sha256 变了（%s）—— 先读 diff、更新 UPSTREAM.md，再改这里的常量" % sha)
    src = raw.decode("utf-8")
    cases = []
    for name, state, seg, poles in _CASE.findall(src):
        seg = [int(x) for x in seg.replace(" ", "").split(",") if x]
        poles = [float(x) for x in poles.replace(" ", "").split(",") if x]
        ours = confirmed(build_segments(pens_of(poles)))
        rust = rust_confirmed(seg)
        c = dict(name=name, poles=poles, upstream_state=state, upstream_segmented=seg,
                 rust_confirmed=rust, ours_confirmed=ours)
        if name in CALIBER:
            kind, why, cite = CALIBER[name]
            c.update(verdict="caliber", kind=kind, why=why, cite=cite)
        elif ours == rust:
            c.update(verdict="identical")
        else:
            raise SystemExit("%s 跟上游不同、又没登记口径出处：我们 %s vs 上游 %s —— 先回原文判谁对" % (name, ours, rust))
        cases.append(c)
    todo = sorted(set(re.findall(r"fn\s+(\w+)\(\)", src)) - {c["name"] for c in cases} - {"assert_forest_eq"})
    return dict(upstream="https://github.com/chan2zen/rust-chan", commit="1d1cc067be6b636df8c78f89e71fe91ad7a3e220",
                file=UPSTREAM_FILE, file_sha256=sha, skipped_upstream=todo, cases=cases)


def main():
    sys.path.insert(0, ROOT)
    from core.segment import build_segments
    if "--extract" in sys.argv:
        d = extract(sys.argv[sys.argv.index("--extract") + 1], build_segments)
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        print("写出 %d 个例子（上游没写完、跳过：%s）" % (len(d["cases"]), d["skipped_upstream"]))
        return 0
    cases = load()["cases"]
    bad = check(build_segments, cases)
    n_id = sum(c["verdict"] == "identical" for c in cases)
    print("rust-chan %d 例：逐位相同 %d · 口径不同（有原文出处）%d · 问题 %d"
          % (len(cases), n_id, len(cases) - n_id, len(bad)))
    for b in bad:
        print("  ✗", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
