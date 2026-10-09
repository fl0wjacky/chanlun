#!/usr/bin/env bash
# 上线前一道门（card-9b0fe913-758）：数据那半（Python 检查）＋ 渲染那半（前端 e2e）按顺序跑，一张表收账。
#
#   tools/predeploy.sh          # 五套 Python 检查 + trend_check --self-test + seg_prefix_check（含 --self-test）+ live_seg_check
#                               #   ＋ **六把 web 尺（主跑 + 各自自检各一条，10-07 接进来，card-b6609942-1ad）**
#                               #   ＋ 前端回归（ghost / more / more --selftest / readout / measure / fs_drag）
#   tools/predeploy.sh --all    # 再加 4 套单卡证据工装（macd_axis / mobile_share / readout_swap_probe / subhead_slot_probe）
#   tools/predeploy.sh --expect <sha> [--all]   # 只在 HEAD 就是这笔、且没有未提交改动时才跑；对不上 ⇒ exit=2（没比成），一格都不跑
#                                               # （也认环境变量 EXPECT_SHA）。card-a1ea0209-015：10-06 worktree 没建成，
#                                               # 闸在旧树 8b9537b 上照跑、报全绿 —— 闸照实印了 HEAD，但没人拿它跟「要测的那笔」比。
#
# 环境变量（都可不给）：
#   PYTHON     跑 Python 检查和临时后台用的解释器，默认 python3
#   NODE       默认 node；前端 e2e 要能 require('playwright')（NODE_PATH / PLAYWRIGHT_BROWSERS_PATH 照常从环境继承）
#
# 退出码：0 全绿 ／ 1 有格子红了 ／ 2 有一步没比成或没执行（浏览器起不来、后台起不来、e2e 回 2/3）——
#   「没比成」绝不当绿，也不塌进 1（Nova 10-05 定）。红和没比成同时有 ⇒ 1。
# 红线（部署细节不进仓库）：临时后台起在**随机空闲端口**、只绑回环；脚本里不写线上端口、隧道、本机路径。
set -u
cd "$(dirname "$0")/.." || exit 2
PY=${PYTHON:-python3}
NODE=${NODE:-node}
ALL=0
EXPECT=${EXPECT_SHA:-}
while [ $# -gt 0 ]; do
  case "$1" in
    --all) ALL=1 ;;
    --expect) shift; EXPECT=${1:-} ;;
    *) echo "不认识的参数：$1" >&2; exit 2 ;;
  esac
  shift
done

RESULTS=()
RED=0
NOTRUN=0
record() {  # 名字 结果(绿/红/没比成/未执行) 说明
  RESULTS+=("$(printf '%-28s %-6s %s' "$1" "$2" "$3")")
  case "$2" in 红) RED=1 ;; 绿) ;; *) NOTRUN=1 ;; esac
}
pick() {  # 日志 正则 head|tail —— 说明栏：grep 不到就兜底印「rc＋日志最后一行」（Nova 10-05 ②）
  local m
  m=$(grep -E "$2" "$1" | "$3" -1)
  if [ -z "$m" ]; then
    m=$(grep -v '^[[:space:]]*$' "$1" | tail -1)
    m="rc=$rc ${m:-（日志是空的）}"
  fi
  printf '%s' "$m" | cut -c1-80
}
KEPT=()
keep() {  # 不是绿的那一步：日志和截图留着，最后印位置（Nova 10-05 ③）
  KEPT+=("$1：$2")
}
tmpname() {  # 只印临时目录下的名字，不印本机绝对路径（Nova 10-05 12:39）：表可以直接贴
  local t=${TMPDIR:-}
  t=${t%/}
  if [ -n "$t" ] && [ "${1#"$t"/}" != "$1" ]; then printf '$TMPDIR/%s' "${1#"$t"/}"; else printf '%s' "$1"; fi
}

# ---- 表头：版本，不印路径（Nova 10-05 ④）----
PYV=$("$PY" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || echo 无)
PIL=$("$PY" -c 'import PIL; print(PIL.__version__)' 2>/dev/null || echo 无)
NODEV=$("$NODE" --version 2>/dev/null || echo 无)
PWV=$("$NODE" -e "console.log(require('playwright/package.json').version)" 2>/dev/null || echo 无)
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo 不在 git 里)
DIRTY=0
git diff --quiet HEAD -- 2>/dev/null || { DIRTY=1; HEAD_SHA="$HEAD_SHA（有未提交的改动）"; }
if [ -n "$EXPECT" ]; then
  # 要测的那笔先解析成全 sha（给的是短 sha／分支名都行）；解析不了、HEAD 不是它、或有未提交改动 ⇒ 一格都不跑，exit=2
  WANT=$(git rev-parse --verify --quiet "$EXPECT^{commit}" 2>/dev/null || true)
  HAVE=$(git rev-parse HEAD 2>/dev/null || true)
  if [ -z "$WANT" ] || [ "$WANT" != "$HAVE" ] || [ $DIRTY = 1 ]; then
    echo "================ 上线前检查 ================"
    if [ -z "$WANT" ]; then why="这台仓库里解析不出这笔：没 fetch？"
    elif [ "$WANT" != "$HAVE" ]; then why="HEAD 不是这笔"
    else why="HEAD 对，但有未提交的改动"; fi
    echo "HEAD $HEAD_SHA ≠ 要测的 $EXPECT（$why）"
    echo "⇒ 测的不是要测的那笔：一格都没跑，不算通过（exit=2）"
    exit 2
  fi
fi

# ---- 数据那半：Python 检查（每一套自己就是 0 过 / 非 0 不过）----
# trend_check --self-test：反向验证（拿掉规则 ⇒ 必须变／必须报）每趟都跑，不靠手动记得（Nova 10-06，card-3edd7fb3）。
# live_seg_check：线上 15 张图现拉现算跑 check_segments，报错就拦（已知例外列在脚本里、写明卡号；拉不到 ⇒ 没比成）。约 50 秒，要联网。
# seg_prefix_check：线段已确认段逐笔加长只增不撤（card-753bd03a 合并条件；Pine 逐根续扫押的就是它）。整串 306 秒（zec15 一张 258 秒，平方级），10-08 起按前缀区间切片多进程跑（SEG_PREFIX_JOBS，默认 4）。
#   它退 3 ＝ 某条探针没响 ＝ 那条检查没牙 ⇒ 记红，不记「没比成」。条目里带参数，所以下面 $chk 不加引号（路径无空格）。
#
# ★★ 六把 web 尺接进来（card-b6609942-1ad，Iris 10-07）：在 10-07 之前，这一串里**只有**
#    `web/check_parity.py` 一把尺，①②④⑤⑥ 全靠人记得手跑 —— 于是 `web_more_check`
#    （05bce7a 起）和 `web_footer_check`（dac61cb 起）**同时在 main 上红了一整天**（约 41 小时），
#    这道门一路是绿的。现在六把**主跑 + 各自自检**都在这儿，每条自己 0 过 / 非 0 不过。
#  ★ 自检条目为什么必须单列：自检证明的是「每格探针都有牙」（改坏了它会响），**不证明
#    「期望值跟代码对得上」**。10-07 实测：② 的自检 17/17 全绿，而它的主跑是红的 ——
#    两条是不同的轴，只跑一条正好会放过上面那种「尺子旧了」的红。
#  ★ 拼法不统一（照各自 usage 头里写的那个写）：③ `check_parity` 是 `--self-test`（带连字符），
#    其余五把是 `--selftest`；本门里 trend/seg_prefix/levels 三条也用的是 `--self-test`。
#    六把现在**两种拼法都认**（Iris f7e7f2f），所以哪种都不会被静默吞掉；门里保持混写只是为了
#    跟每个脚本自己的文档一致。
#  ★ ①③ 要 PIL（① 经 `render/style.py`，③ 经 `from render.style import CHART`）⇒ 缺 PIL 时它们
#    打顶格的 `ModuleNotFoundError`，按下面「崩了」那条归 **rc=99 记「没比成」**（不是红）。标题那行
#    印的 `PIL 无` 就是给这个看的：门要用带 PIL 的解释器跑（`PYTHON=`）。
# ★ speed_gate（card-5a1f2ec2-650，Nova 10-08 18:48）：每张图整段划一次（analyze＋trend_v3），跟 origin/main 同机交替比，
#   任何一张（两边慢的那个 ≥100ms）慢过 1.5 倍 ⇒ 红；HEAD 一轮超过基准一轮的 3 倍（至少 20s）直接掐掉记红。约 35 秒，
#   自检约 50 秒（HEAD 对 HEAD 必须绿；build_segments 每次多划一遍必须红）。解析不出 origin/main（没 fetch）⇒ rc=2 没比成。
#   缘由：L77 那一版事后手跑才发现慢，别的尺量的全是「对不对」。
# ★ check_abuse --self-test（card-79464e38-458，10-08 接进来）：15 种改坏后台，主跑必须各自红；一臂一个子进程、5 个并行，约 2 分 20 秒。
#   接进来之前没人跑它，第 12 臂（替身不收 cut/pen_min）崩了不知多久。一臂崩了算没牙（rc=3 ⇒ 记红）。
# ★ check_closedue（card-7d3e8748-3d3）：收盘前 1 秒请求过、收盘后打开，照页面真的补数节奏（常量从 app.js 读）敲，
#   10 秒内必须拿到新那根，每格每根最多多拉币安 1 次。假钟假币安，约 12 秒；自检把 _close_due 摘掉必须红。
# ★ 并行池（card-b71b1600-253）：条目交给 tools/predeploy_pool.py 跑，每条的输出 / 退出码 / 用时落到临时目录；再**按原顺序**
#   一条条读回来，分类、记表跟原来一字不差，每格说明栏开头多一个这一条的用时。
#   **默认 1 路（Nova 10-08 23:01 定）**：10-08 干净机器上量过 4 路，Python 那半 457 → 341 秒，可单条被挤慢（selfcheck 46 → 176 秒，
#   seg_prefix 自己又起 4 个进程，加上机器底噪，超订了），整门只省 129 秒。代码留着，`PREDEPLOY_JOBS=N` 可开；
#   开的话速度门照样在池子之后单独串跑、check_abuse 排池子末尾。两种跑法 37 格逐条绿红一样（10-08 对拍过）。
#   为什么不按「改了哪些文件才跑」挑：10-08 web_more_check 那一格，恰好是「谁也没想到会碰到它」的红。
# ★ l77_check（card-c784a101-791，第五批）：L77 第二支硬合 —— 夹具 1300/1600/1317、合段时刻逐笔对拍、随机 4000 违规 0、
#   独立复核 case 4 的牙（终点前后挪、反弹一笔、A 一笔、R 三笔没重叠）；自检关掉 L77_MERGE 必红。约 15 秒。
# ★ render_smoke（card-bb93e074-3c6，Nova 10-09 00:39）：weak 下线时 render/full_common.py 还读 s["weak"]，整门没走到出图这条路。
#   拿 zec15 跑一次 chart_full_smooth.render，不炸、出得了图就绿；自检让买卖点少一个出图要读的字段必红。约 3 秒，要 PIL。
CHECKS=(tools/selfcheck.py web/check_parity.py "web/check_parity.py --self-test" web/check_abuse.py "web/check_abuse.py --self-test" web/check_closedue.py "web/check_closedue.py --self-test" web/check_assets.py "tools/pine_lockstep.py --head HEAD" "notes/pine-incremental-seg.py --self-test" "notes/pine-incremental-seg.py --tail 60" "tools/trend_check.py --self-test" tools/speed_gate.py "tools/speed_gate.py --self-test" tools/seg_prefix_check.py "tools/seg_prefix_check.py --self-test" tools/l77_check.py "tools/l77_check.py --self-test" tools/render_smoke.py "tools/render_smoke.py --self-test" tools/live_seg_check.py tools/levels_check.py "tools/levels_check.py --self-test" "tools/j18_check.py --self-test" "tools/j19_check.py --self-test" "tools/j17_check.py --self-test" tools/web_theme_sync.py "tools/web_theme_sync.py --selftest" tools/web_footer_check.py "tools/web_footer_check.py --selftest" tools/web_fmt_check.py "tools/web_fmt_check.py --selftest" tools/web_fitbox_check.py "tools/web_fitbox_check.py --selftest" tools/web_more_check.py "tools/web_more_check.py --selftest")
POOLDIR=$(mktemp -d)
POOL_T0=$(date +%s)
"$PY" tools/predeploy_pool.py --dir "$POOLDIR" --jobs "${PREDEPLOY_JOBS:-1}" --python "$PY" -- "${CHECKS[@]}"
POOL_SEC=$(( $(date +%s) - POOL_T0 ))
ci=0
for chk in "${CHECKS[@]}"; do
  log="$POOLDIR/$ci.log"
  rc=$(cat "$POOLDIR/$ci.rc" 2>/dev/null || echo 97)       # 97：池子没给这一条落退出码（不该发生）⇒ 记「没比成」
  sec=$(cat "$POOLDIR/$ci.sec" 2>/dev/null || echo "?")
  ci=$((ci + 1))
  case $chk in *--self-test) [ $rc = 3 ] && rc=1 ;; esac
  # Python 崩了（缺包、Traceback）退的也是 1，跟「比了、红了」同码 ⇒ 先看日志分开（Iris 核 167a32a 时逮到）
  if [ $rc = 1 ] && grep -qE '^(Traceback|ModuleNotFoundError|ImportError)' "$log"; then rc=99; fi
  # selfcheck 自己有一栏「查不了 / 跑不了」（缺字体、缺版式工具）而引擎违规是 0 ⇒ 那是环境没备齐，不是红
  if [ $rc = 1 ] && grep -E '^退出原因' "$log" | grep -q '总违规=0' && grep -E '^退出原因' "$log" | grep -qE '查不了|跑不了'; then rc=98; fi
  case $rc in
    0) record "$chk" 绿 "${sec}s" ;;
    1) record "$chk" 红 "${sec}s $(pick "$log" '✗|不过|退出原因' tail)" ;;
    99) record "$chk" 没比成 "${sec}s 崩了：$(pick "$log" '^[A-Za-z]*Error' tail)" ;;
    98) record "$chk" 没比成 "${sec}s 环境没备齐：$(grep -E '^退出原因' "$log" | grep -oE '[^ ]+=(查不了|跑不了)' | tr '\n' ' ')" ;;
    *) record "$chk" 没比成 "${sec}s rc=$rc $(grep -v '^[[:space:]]*$' "$log" | tail -1 | cut -c1-70)" ;;
  esac
  if [ $rc = 0 ]; then rm -f "$log"; else keep "$chk" "日志 $(tmpname "$log")"; fi
done

# ---- 渲染那半：前端 e2e ----
# 一格可以带开关：「文件 开关…」用空格隔开（下面跑的时候按空格拆）。`web_more_e2e.js --selftest` 是 ㉑ 那条竞态的牙：
#   故意把最后几档扣住，旧写法（死等 3 秒）必须红、现写法必须绿，两条都对才 rc=0（card-c5a625b8-a14，Nova 10-08 23:52 定接进来）。
SUITES=(tools/web_ghost_e2e.js tools/web_more_e2e.js "tools/web_more_e2e.js --selftest" tools/web_readout_e2e.js tools/web_measure_e2e.js tools/web_fs_drag_e2e.js)
# ★ web_fs_drag_e2e（card-c90f0f08-3ac）：拖过再进/出全屏，视口不许跳回最初那一屏。web_measure_e2e 的全屏格是**没拖过**就进，量不到这个。
# ★ subhead_slot_probe 挂在 --all 档、**不进默认档**（Nova 2026-10-05 16:04）：它要真后台连点十二次开关、
#   跑将近一分钟，只有上线前那一趟值这个时间。它钉的是「副图页头拿格高 0 摆位置」（card-9b0fe913-758）。
# ★★ 它跟 68decdd 是**一对**：改前那一棵树（`e494d90`）上它 5/12 红。所以这支**必须在 68decdd 之后并**
#   —— 先并它再并 68decdd，中间的 main 上 `--all` 就是红的（那不是它报错，是它说的实话）。
[ $ALL = 1 ] && SUITES+=(tools/web_macd_axis.js tools/web_mobile_share.js tools/web_readout_swap_probe.js tools/web_subhead_slot_probe.js)

frontend_skip() {  # 原因 —— 浏览器 / 后台起不来：每一套都记「未执行」，不许当绿
  for s in "${SUITES[@]}"; do record "$s" 未执行 "前端未执行：$1"; done
}

if ! command -v "$NODE" >/dev/null 2>&1; then
  frontend_skip "找不到 node"
elif ! "$NODE" -e "require('playwright').chromium.launch().then(b => b.close())" >/dev/null 2>&1; then
  frontend_skip "playwright / chromium 起不来"
else
  PORT=$("$PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
  SRVLOG=$(mktemp)
  "$PY" web/server.py --port "$PORT" --no-prewarm >"$SRVLOG" 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null; wait $SRV 2>/dev/null' EXIT
  up=0
  for _ in $(seq 1 60); do
    if "$PY" -c "import urllib.request, sys; urllib.request.urlopen('http://127.0.0.1:$PORT/api/meta', timeout=2)" 2>/dev/null; then
      up=1; break
    fi
    sleep 0.5
  done
  if [ $up = 0 ]; then
    frontend_skip "临时后台 30 秒内没起来（$(tail -1 "$SRVLOG" | cut -c1-60)）"
    keep "临时后台" "日志 $(tmpname "$SRVLOG")"
  else
    export E2E_URL="http://127.0.0.1:$PORT/"   # 7 套都先读它（Iris 2140c0d），不用管各自收第几个参数
    for s in "${SUITES[@]}"; do
      out=$(mktemp -d)
      log=$(mktemp)
      read -r -a argv <<<"$s"                     # 「文件 开关…」拆开：文件在前，输出目录照旧放在开关后面
      "$NODE" "${argv[@]}" "$out" >"$log" 2>&1
      rc=$?
      case $rc in
        0) g=$(pick "$log" '[0-9]+/[0-9]+ *(过|绿)|都对' tail | sed 's/　*截图.*//')
           record "$s" 绿 "$g" ;;
        1) record "$s" 红 "$(pick "$log" '✗' head)" ;;
        2|3) m=$(pick "$log" '✗|炸了' head); case $m in rc=*) ;; *) m="rc=$rc $m" ;; esac
             record "$s" 没比成 "$m" ;;
        *) record "$s" 没比成 "rc=$rc（意料之外的退出码）" ;;
      esac
      if [ $rc = 0 ]; then rm -rf "$out" "$log"; else keep "$s" "日志 $(tmpname "$log") ／ 截图 $(tmpname "$out")"; fi
    done
    rm -f "$SRVLOG"
  fi
fi

echo "================ 上线前检查 ================"
echo "HEAD $HEAD_SHA · python $PYV（PIL $PIL）· node $NODEV · playwright $PWV · 临时端口 ${PORT:-没起}"
echo "Python 那半墙钟 ${POOL_SEC}s（并行 ${PREDEPLOY_JOBS:-1} 路；速度门在池子之后单独串跑；每格「说明」栏开头是这一条自己的用时）"
for line in "${RESULTS[@]}"; do echo "$line"; done
if [ ${#KEPT[@]} -gt 0 ]; then
  echo "---- 没过的那几步，日志和截图留着 ----"
  for line in "${KEPT[@]}"; do echo "$line"; done
fi
if [ $RED = 1 ]; then
  echo "⇒ 有格子红了：不许上线（exit=1）"; exit 1
elif [ $NOTRUN = 1 ]; then
  echo "⇒ 有一步没比成 / 没执行：不算通过（exit=2）"; exit 2
fi
echo "⇒ 全绿（exit=0）"
exit 0
