# Nova 独立核验 v1：引文 × 坐标。不复用队友任何脚本。
# 对 docs 下每一行：抽出「…」块与 L课:行(-行) 坐标；
#  A 级：块在全书（去换行）里根本找不到
#  B 级：同一行带了坐标，但块不在所引那几课的所引行区间（±2 行容差）里
import re, os, sys, glob, json
REPO = sys.argv[1] if len(sys.argv) > 1 else '.'
T = 'archive/chanlun108/text'
L = {}
for f in sorted(os.listdir(T)):
    n = int(re.findall(r'\d+', f)[0])
    L[n] = open(os.path.join(T, f), encoding='utf-8').read().replace('\r', '').split('\n')
norm = lambda s: re.sub(r'[\s↵*`]', '', s)
whole = {n: norm(''.join(v)) for n, v in L.items()}
ALL = ''.join(whole[n] for n in sorted(whole))
def seg(n, a, b):
    a = max(1, a - 2); b = min(len(L[n]), b + 2)
    return norm(''.join(L[n][a-1:b]))
COORD = re.compile(r'L(\d{1,3}):(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?')
Q = re.compile(r'「([^「」]{4,})」')
files = sorted(glob.glob(REPO + '/docs/concepts/inventory_*.md') + glob.glob(REPO + '/docs/spec/*.md') + [REPO + '/docs/concepts/README.md', REPO + '/docs/concepts/兜底_nova.md'])
rep = {'A': [], 'B': [], 'ok': 0, 'blocks': 0, 'coordblocks': 0}
for fp in files:
    for i, line in enumerate(open(fp, encoding='utf-8'), 1):
        qs = Q.findall(line)
        if not qs: continue
        cs = []; last = None
        for m in re.finditer(r'L(\d{1,3}):(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?|(?<![L\d])[`]?:(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?|第\s*(\d{1,3})\s*课', line):
            if m.group(1):
                n=int(m.group(1)); a=int(m.group(2)); b=int(m.group(3) or a); last=n
                if n in L: cs.append((n,a,b))
            elif m.group(4) and last:
                a=int(m.group(4)); b=int(m.group(5) or a)
                if last in L: cs.append((last,a,b))
            elif m.group(6):
                n=int(m.group(6))
                if n in L: cs.append((n,1,len(L[n])))
        for q in qs:
            rep['blocks'] += 1
            parts = [p for p in re.split(r'…+|\.\.\.+', q) if norm(p)]
            if not parts: continue
            if not all(norm(p) in ALL for p in parts):
                rep['A'].append((os.path.relpath(fp, REPO), i, q[:50])); continue
            if cs:
                rep['coordblocks'] += 1
                hit = any(all(norm(p) in seg(n, a, b) for p in parts) for n, a, b in cs)
                if not hit:
                    # 再放宽：只要在所引那些课里任意位置
                    inl = any(all(norm(p) in whole[n] for p in parts) for n, a, b in cs)
                    rep['B'].append((os.path.relpath(fp, REPO), i, q[:40], [f'L{n}:{a}-{b}' for n, a, b in cs][:3], 'same-lesson' if inl else 'other-lesson'))
                    continue
            rep['ok'] += 1
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}, ensure_ascii=False))
json.dump(rep, open('/tmp/v1_out.json', 'w'), ensure_ascii=False, indent=0)
