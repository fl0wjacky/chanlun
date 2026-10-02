# ③（线段）pine 侧设计 —— A 增量、B 整段（待 Iris 配色合完再动手）

> **已修正（2026-10-02）**：同步三路里「尾端点被换 ⇒ 只重推最后一笔」是错的 —— 换最后那根笔
> 会翻动 `openingOverlaps` 倒数几格、续扫的 i 只增不回 ⇒ 缓存段 stale。收成两路：**纯追加走增量，
> 其余（尾换 / 缩水 / 跳变 / 深处回改）一律整段重算**。见 `notes/seg-sync-skipflip.md`。

## 决策（Nova 定 + 我验证）

`build_segments` 对 **featDir=A 前缀单调**（9 份数据 + 2000 随机序列 0 次撤销）、
对 **featDir=B 非单调**（反向分型形成后可被后笔包含撤销，zec15 1 次 / 2000 随机 27 次）。
→ **A 走增量、B 保持整段重算**。不改 engine、不问小栋。`featDir` 默认 A。

## 现状（main 172e95a / 我的支 85b3ebf，pine 1033 行）

- `buildSegments(array<Unit> P) =>`（函数，约 :581）—— 整段重算。用 `endPen<0` 哨兵 + `stop` 布尔，
  `born` 存在局部。`caseAt` 内部读全局 `featModeB`（`:37` = `featDir == "B…"`），所以 mode 是**图表级输入**，不是参数。
- islast（`:908`）里 `:915 pens = zUnits(zFx, zSeq)` 摊平、`:916 segs = buildSegments(pens)`、
  `:917-920 done = 非 live 段`、`:921 pcs = findCenters(pens)`、`:922 scs = findCenters(done)`。
- 逐根侧：`:241 zRefx(...)`（① 分型）、`:411 zPenStep(...)`（② 笔，往 zSeq 追加端点）。**③ 的钩子就在 zPenStep 之后。**

## 增量状态（新增 var，放在 ② 的 `zSeq/zPend` 那组旁边）

```
var array<Unit> segs   = array.new<Unit>()   // 已确认段（只增）
var int         segI   = 0                    // 扫描位置 = 上一段 endPen + 1
var int         segBorn = 0                   // 本段方向确立的破位笔（case-1 的 at；case-2 归 0）
```

## 逐根续扫（zSegStep，镜像 buildSegments 的内层，从 (segI, segBorn) 起）

与 Python `IncSegments.feed` 逐支对应，但用 pine 的 `endPen<0` / `stop` 形状：

```
zSegStep(pens, segs, segI, segBorn):
  n = pens.size(); i = segI; born = segBorn
  bool stop = false
  while i + 2 < n and not stop
      if not openingOverlaps(pens, i):  i += 1; continue
      up = isUp(pens.get(i)); k = i + 2
      while k < born: k += 2
      int endPen = -1; int res = -1
      while k < n - 1 and endPen < 0
          [cse, at] = caseAt(pens, i, k, up)
          if cse > 0: endPen := k; res := cse == 1 ? at : 0
          else: k += 2; if at >= 0: while k < at: k += 2
      if endPen < 0: stop := true
      else: born := res; segs.push(mkSeg(pens, i, endPen, false)); i := endPen + 1
  [segI, segBorn] := [i, born]     // 写回 var
```

★ 每根 bar 最多确认 1 段（实际大多 0 段），平摊 O(1)；不摊平全量 pens —— `pens` 本身就是 `zUnits(zFx, zSeq)`
  的产物，续扫只从 `segI` 起读，摊平这一步仍可只在 islast 做（续扫要的 pens 下标 ≥ segI，读 `zUnits` 是 O(n)，
  这里要斟酌：要么每根摊平 O(n)、要么只摊 segI 之后的尾巴 —— **实现时定，先记一笔**）。

## islast 分叉

```
if featModeB
    segs = buildSegments(pens)          // B：整段（现状不动）
else
    // A：segs 已增量维护，只补 live 尾巴
    segs = segs  // 已确认段
    if n - segI >= 3
        segs.push(mkSeg(pens, segI, n - 1, true))   // live 尾巴（不落 var，只画）
```

`done`（非 live）仍然 `for s in segs: if not s.live: done.push(s)` —— live 尾巴是临时补的、不带入下一次。

## 关键点 / 坑

1. **live 尾巴不能写回 var `segs`**：它每根都在变；只画不存。确认段才 push 进 var。
2. **B 路径完全不动**：`buildSegments` 原样保留，就是 B 的整段参照（也正好当 lockstep 的"引擎对照"对象）。
3. **caseAt 用全局 featModeB**：A 增量路径下 featModeB=false，`caseAt` 内部 `featStd(..., featModeB)` 自动走 A 方向 —— 不用改 caseAt。
4. **空表坑**：续扫的 `while k < born`、`while k < n-1` 都是 `to` 有界；`n-1` 在 n<2 时是 0 或负 —— 外层 `i+2 < n` 已经挡住了 n 太小，但照旧每条倒序/有界 for 前判空。
5. **验收三层**：解析 + 引擎对照 0 不一致（Python `notes/pine-incremental-seg.py` 已证明 A 逐前缀 == 整段；pine 侧要 lockstep 两层绿）+ 小栋真机开图。

## 依赖 / 顺序

Iris 配色（`card-97728a8a-ae6`）合完 → 文件回我 → 动 pine 做 ③ → 解析 + 参照 + lockstep → 交 Nova 核 → 小栋开图。
我不和 Iris 同时碰 pine。
