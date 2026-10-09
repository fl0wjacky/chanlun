# -*- coding: utf-8 -*-
"""T6（上线清单 G2，Atlas 对表 a78fd69，Nova 10-09 10:21 定）：同级别正式口径的**轻量前缀回放**，接进 predeploy。

问一件事：K 线一根根往后长，**已经标 confirmed 的刀，后来有没有消失、有没有回到 pending**？两样都必须是 0（读法-①D：确认了就不收回）。
口径＝正式版全开（同级别＋S9＋甲＋首中枢豁免＋死因）＋PEN_FINAL_LOCK（P1／P2）；开关只在这一跑里临时翻，跑完复原。
前缀按「全图笔终点的后一根」取（同 notes/zg4/engstate.py 全量回放，那份 25 张；这里挑两份短夹具，几秒跑完）。

用法：
    python3 tools/sl_replay_check.py              # 两份夹具，回翻／消失须 0
    python3 tools/sl_replay_check.py --self-test  # 两条正臂：故意让一把确认的刀回翻、故意让一把确认的刀消失 ⇒ 都必须红
退出码：0 过；1 有回翻／消失；3 自检正臂没红（这把尺不算数）
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
from core.analyze import analyze                  # noqa: E402
import core.trend as T                            # noqa: E402
import core.pen as PEN                            # noqa: E402
from config import tick_of                        # noqa: E402

FIXTURES = ("zec_2h.json", "zec_1h.json")          # 都有确认过的 D2；zec_1h 还有确认过的 S5
SL_FLAGS = dict(SAME_LEVEL=True, SAME_LEVEL_D2=True, SAME_LEVEL_D6="fallback", SL_FIRST_EXEMPT=True, SAME_LEVEL_DEATH=True)


def replay(fn, tamper=None):
    """→ (问题列表, 确认过的刀数)。tamper(c, bounds) 给自检用：在第 c 个前缀上原地改 bounds。"""
    old = {k: getattr(T, k) for k in SL_FLAGS}; lk = PEN.PEN_FINAL_LOCK
    try:
        for k, x in SL_FLAGS.items():
            setattr(T, k, x)
        PEN.PEN_FINAL_LOCK = True
        bars = json.load(open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        t = tick_of(fn)
        full = analyze(bars, tick=t)
        cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
        prev, bad, ever = {}, [], set()
        for n, c in enumerate(cuts):
            bs = T.trend_v3(analyze(bars[:c], tick=t))["bounds"]
            if tamper:
                tamper(n, bs)
            cur = {(b["bar"], b["kind"], b["rule"]): b.get("state") for b in bs}
            for k, s in prev.items():
                if s != "confirmed":
                    continue
                if k not in cur:
                    bad.append("%s 前缀 %d：确认过的 %s 刀 %d %s 消失了" % (fn, c, k[2], k[0], k[1]))
                elif cur[k] != "confirmed":
                    bad.append("%s 前缀 %d：确认过的 %s 刀 %d %s 回到 %s" % (fn, c, k[2], k[0], k[1], cur[k]))
            ever |= {k for k, s in cur.items() if s == "confirmed"}
            prev = cur
        return bad, len(ever)
    finally:
        for k, x in old.items():
            setattr(T, k, x)
        PEN.PEN_FINAL_LOCK = lk


def main():
    bad, total = [], 0
    for fn in FIXTURES:
        b, n = replay(fn)
        print("%s %s：确认过 %d 把，回翻／消失 %d" % ("✓" if not b else "✗", fn, n, len(b)))
        bad += b; total += n
    for x in bad[:5]:
        print("   ", x)
    if not total:
        print("★ 两份夹具一把确认的刀都没有 ⇒ 这把尺空转（exit=3）")
        return 3
    print("全部通过" if not bad else "%d 处不过" % len(bad))
    return 1 if bad else 0


def self_test():
    """正臂①：第一次出现 confirmed 以后的下一个前缀，把它改回 pending ⇒ 必须报「回到」；正臂②：同样位置把它删掉 ⇒ 必须报「消失」。"""
    miss = 0
    for name, act, word in (("回翻", lambda b: b.__setitem__("state", "pending"), "回到"), ("消失", None, "消失")):
        seen = {}
        def tamper(n, bs, act=act, seen=seen):
            if "hit" in seen and n == seen["hit"] + 1:
                tgt = [b for b in bs if (b["bar"], b["kind"]) == seen["key"]]
                if tgt:
                    act(tgt[0]) if act else bs.remove(tgt[0])
            if "hit" not in seen:
                c = [b for b in bs if b.get("state") == "confirmed"]
                if c:
                    seen["hit"], seen["key"] = n, (c[0]["bar"], c[0]["kind"])
        b, _ = replay(FIXTURES[0], tamper)
        ok = any(word in x for x in b)
        print("%s 正臂「故意%s」⇒ 报出 %d 处（例 %s）" % ("✓" if ok else "✗", name, len(b), b[:1]))
        miss += not ok
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else main())
