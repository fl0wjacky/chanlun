#!/usr/bin/env bash
# 上线前一道门（card-9b0fe913-758）：数据那半（Python 检查）＋ 渲染那半（前端 e2e）按顺序跑，一张表收账。
#
#   tools/predeploy.sh          # 五套 Python 检查 + cut_check + 4 套前端回归（ghost / more / readout / measure）
#   tools/predeploy.sh --all    # 再加 3 套单卡证据工装（macd_axis / mobile_share / readout_swap_probe）
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

# ---- 数据那半：Python 检查（每一套自己就是 0 过 / 非 0 不过）----
for chk in tools/selfcheck.py web/check_parity.py web/check_abuse.py web/check_assets.py tools/pine_lockstep.py tools/cut_check.py; do
  log=$(mktemp)
  "$PY" "$chk" >"$log" 2>&1
  rc=$?
  case $rc in
    0) record "$chk" 绿 "" ;;
    1) record "$chk" 红 "$(grep -E '✗|不过|退出原因' "$log" | tail -1 | cut -c1-80)" ;;
    *) record "$chk" 没比成 "rc=$rc $(tail -1 "$log" | cut -c1-70)" ;;
  esac
  rm -f "$log"
done

# ---- 渲染那半：前端 e2e ----
SUITES=(tools/web_ghost_e2e.js tools/web_more_e2e.js tools/web_readout_e2e.js tools/web_measure_e2e.js)
[ $ALL = 1 ] && SUITES+=(tools/web_macd_axis.js tools/web_mobile_share.js tools/web_readout_swap_probe.js)

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
  trap 'kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; rm -f "$SRVLOG"' EXIT
  up=0
  for _ in $(seq 1 60); do
    if "$PY" -c "import urllib.request, sys; urllib.request.urlopen('http://127.0.0.1:$PORT/api/meta', timeout=2)" 2>/dev/null; then
      up=1; break
    fi
    sleep 0.5
  done
  if [ $up = 0 ]; then
    frontend_skip "临时后台 30 秒内没起来（$(tail -1 "$SRVLOG" | cut -c1-60)）"
  else
    export E2E_URL="http://127.0.0.1:$PORT/"   # 7 套都先读它（Iris 2140c0d），不用管各自收第几个参数
    for s in "${SUITES[@]}"; do
      out=$(mktemp -d)
      log=$(mktemp)
      "$NODE" "$s" "$out" >"$log" 2>&1
      rc=$?
      case $rc in
        0) record "$s" 绿 "$(grep -E '[0-9]+/[0-9]+ *(过|绿)' "$log" | tail -1 | sed 's/　*截图.*//' | cut -c1-60)" ;;
        1) record "$s" 红 "$(grep -E '✗' "$log" | head -1 | cut -c1-80)" ;;
        2|3) record "$s" 没比成 "rc=$rc $(grep -E '✗|炸了' "$log" | head -1 | cut -c1-70)" ;;
        *) record "$s" 没比成 "rc=$rc（意料之外的退出码）" ;;
      esac
      rm -rf "$out" "$log"
    done
  fi
fi

echo "================ 上线前检查 ================"
for line in "${RESULTS[@]}"; do echo "$line"; done
if [ $RED = 1 ]; then
  echo "⇒ 有格子红了：不许上线（exit=1）"; exit 1
elif [ $NOTRUN = 1 ]; then
  echo "⇒ 有一步没比成 / 没执行：不算通过（exit=2）"; exit 2
fi
echo "⇒ 全绿（exit=0）"
exit 0
