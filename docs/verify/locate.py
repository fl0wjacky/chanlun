import json,re,os
T='archive/chanlun108/text'
L={int(re.findall(r'\d+',f)[0]):open(os.path.join(T,f),encoding='utf-8').read().split('\n') for f in os.listdir(T)}
norm=lambda s:re.sub(r'[\s↵*`]','',s)
def where(q):
    p=norm(re.split(r'…+',q)[0])[:12]
    out=[]
    for n in sorted(L):
        for i in range(len(L[n])):
            w=norm(''.join(L[n][i:i+3]))
            if w.startswith(p) or (p in w and p not in norm(''.join(L[n][i+1:i+3]))):
                out.append(f'L{n}:{i+1}');break
    return out[:4]
r=json.load(open('/tmp/v1_out.json'))
long=[x for x in r['B'] if len(re.sub(r'\s','',x[2]))>=10]
res=[]
for x in long:
    res.append((x[0].split('/')[-1],x[1],x[2][:24],x[3][:2],where(x[2])))
json.dump(res,open('/tmp/long_located.json','w'),ensure_ascii=False)
for t in res[:40]: print(t)
