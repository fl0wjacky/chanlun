# 盘整组复核：用**前端那一份** `pzGroups`（web/layers.js，>>> PZ_GROUPS）数组，不另写一套判据。
# 段由 core.trend.trend_v3 出（跟线上载荷同一个函数），交给 node 跑 layers.js 里那个函数。
# 用法（仓根目录）：python3 notes/b5/pz_crosscheck.py [线上快照.gz]   —— 不给快照就只数 data/ 那 10 份
# 输出：每份一行「名字  组数  各组段数」，最后一行合计（跟 Atlas notes/b5/pz_merge.py 同一批 DATA、同一种快照格式）。
import sys, json, gzip, subprocess
sys.path[:0] = [".", "tools"]
from core.analyze import analyze, analyze_file
from config import tick_of
import core.trend as T
DATA = ["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json","zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
ch = [(f, analyze_file(f)) for f in DATA]
if len(sys.argv) > 1:
    snap = json.loads(gzip.open(sys.argv[1]).read())
    ch += [(k, analyze(snap[k]["bars"], tick=tick_of(syms[k.split()[0]] + "_.json"))) for k in sorted(snap)]
segs = {name: [{k: s[k] for k in ("type", "i0", "i1", "head")} for s in T.trend_v3(r)["segments"]] for name, r in ch}
JS = """
import { pzGroups } from './web/layers.js';
const all = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let g = 0, s = 0;
for (const [name, segs] of Object.entries(all)) {
  const G = pzGroups({ segments: segs }); g += G.length; s += G.reduce((a, x) => a + x.n, 0);
  console.log(name.padEnd(20), G.length, JSON.stringify(G.map((x) => x.n)));
}
console.log('合计', g, '组', s, '段');
"""
JS = "import { createRequire } from 'module'; const require = createRequire(import.meta.url);" + JS
out = subprocess.run(["node", "--input-type=module", "-e", JS], input=json.dumps(segs), capture_output=True, text=True)
print(out.stdout, end=""); print(out.stderr, end="", file=sys.stderr)
sys.exit(out.returncode)
