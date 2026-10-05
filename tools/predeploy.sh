#!/usr/bin/env bash
# 上线前一道门（card-9b0fe913-758）：数据那半（Python 检查）＋ 渲染那半（前端 e2e）按顺序跑，一张表收账。
#
#   tools/predeploy.sh          # 五套 Python 检查 + cut_check + 4 套前端回归（ghost / more / readout / measure）
#   tools/predeploy.sh --all    # 再加 4 套单卡证据工装（macd_axis / mobile_share / readout_swap_probe / subhead_slot_probe）
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
[ "${1:-}" = "--all" ] && ALL=1

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
git diff --quiet HEAD -- 2>/dev/null || HEAD_SHA="$HEAD_SHA（有未提交的改动）"

# ---- 数据那半：Python 检查（每一套自己就是 0 过 / 非 0 不过）----
for chk in tools/selfcheck.py web/check_parity.py web/check_abuse.py web/check_assets.py tools/pine_lockstep.py tools/cut_check.py; do
  log=$(mktemp)
  "$PY" "$chk" >"$log" 2>&1
  rc=$?
  # Python 崩了（缺包、Traceback）退的也是 1，跟「比了、红了」同码 ⇒ 先看日志分开（Iris 核 167a32a 时逮到）
  if [ $rc = 1 ] && grep -qE '^(Traceback|ModuleNotFoundError|ImportError)' "$log"; then rc=99; fi
  # selfcheck 自己有一栏「查不了 / 跑不了」（缺字体、缺版式工具）而引擎违规是 0 ⇒ 那是环境没备齐，不是红
  if [ $rc = 1 ] && grep -E '^退出原因' "$log" | grep -q '总违规=0' && grep -E '^退出原因' "$log" | grep -qE '查不了|跑不了'; then rc=98; fi
  case $rc in
    0) record "$chk" 绿 "" ;;
    1) record "$chk" 红 "$(pick "$log" '✗|不过|退出原因' tail)" ;;
    99) record "$chk" 没比成 "崩了：$(pick "$log" '^[A-Za-z]*Error' tail)" ;;
    98) record "$chk" 没比成 "环境没备齐：$(grep -E '^退出原因' "$log" | grep -oE '[^ ]+=(查不了|跑不了)' | tr '\n' ' ')" ;;
    *) record "$chk" 没比成 "rc=$rc $(grep -v '^[[:space:]]*$' "$log" | tail -1 | cut -c1-70)" ;;
  esac
  if [ $rc = 0 ]; then rm -f "$log"; else keep "$chk" "日志 $(tmpname "$log")"; fi
done

# ---- 渲染那半：前端 e2e ----
SUITES=(tools/web_ghost_e2e.js tools/web_more_e2e.js tools/web_readout_e2e.js tools/web_measure_e2e.js)
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
      "$NODE" "$s" "$out" >"$log" 2>&1
      rc=$?
      case $rc in
        0) record "$s" 绿 "$(pick "$log" '[0-9]+/[0-9]+ *(过|绿)' tail | sed 's/　*截图.*//')" ;;
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
