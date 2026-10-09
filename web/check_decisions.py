# -*- coding: utf-8 -*-
"""决策树网页后端的对账（card-fe3aebd3-819）：起一个临时服务，数据和状态目录都指到临时目录（不碰真的），逐条打接口。

    python3 web/check_decisions.py              # 主跑：各种请求的状态码、存取、历史、不漏路径／口令
    python3 web/check_decisions.py --self-test  # 变异：口令校验拿掉 ⇒ 主跑必须红
退出码：0 过；1 有不过；3 自检变异没红（这把尺不算数）
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server                                     # noqa: E402
import decisions                                  # noqa: E402

SPEC = {"items": [{"id": "S-13", "title": "笔定稿", "options": [{"key": "A"}, {"key": "B"}]},
                  {"id": "R-1", "title": "分解方式", "options": [{"key": "A"}, {"key": "B"}]}]}
TOKEN = "test-token-not-in-repo"          # HTTP 头只能放 latin-1，口令一律 ASCII


def req(port, method, path, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    if token is not None:
        r.add_header("X-Decision-Token", token)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def run(quiet=False):
    tmp = tempfile.mkdtemp()
    saved = (decisions.SPEC, decisions.STATE, decisions.CHOICES, decisions.HISTORY, decisions.TOKEN)
    decisions.SPEC = os.path.join(tmp, "decisions.json")
    decisions.STATE = os.path.join(tmp, "state")
    decisions.CHOICES = os.path.join(decisions.STATE, "decisions-choices.json")
    decisions.HISTORY = os.path.join(decisions.STATE, "decisions-choices.jsonl")
    decisions.TOKEN = os.path.join(decisions.STATE, "decisions.token")
    srv = server.make_server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    bad = []

    def chk(name, ok, got=""):
        if not quiet:
            print("%s %s %s" % ("✓" if ok else "✗", name, "" if ok else got))
        if not ok:
            bad.append(name)

    try:
        P = "/api/decisions/choices"
        c, b = req(port, "GET", "/api/decisions"); chk("数据文件不在 ⇒ 503", c == 503, (c, b))
        with open(decisions.SPEC, "w", encoding="utf-8") as f:
            json.dump(SPEC, f, ensure_ascii=False)
        c, b = req(port, "GET", "/api/decisions"); chk("数据原样返回", c == 200 and json.loads(b) == SPEC, (c, b[:80]))
        c, b = req(port, "GET", "/api/decisions?x=1"); chk("带查询参数 ⇒ 400", c == 400, c)
        c, b = req(port, "GET", P); chk("还没人选过 ⇒ {}", c == 200 and json.loads(b) == {}, (c, b))
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B"}, TOKEN); chk("没配口令文件 ⇒ 503（不是谁都能写）", c == 503, c)
        os.makedirs(decisions.STATE, exist_ok=True)
        with open(decisions.TOKEN, "w", encoding="utf-8") as f:
            f.write(TOKEN + "\n")
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B"}); chk("不带口令 ⇒ 403", c == 403, c)
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B"}, "wrong"); chk("口令错 ⇒ 403", c == 403, c)
        c, b = req(port, "POST", P, {"id": "X-9", "option": "A"}, TOKEN); chk("不认识的条目 ⇒ 400", c == 400, c)
        c, b = req(port, "POST", P, {"id": "S-13", "option": "C"}, TOKEN); chk("不认识的选项 ⇒ 400", c == 400, c)
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B", "evil": 1}, TOKEN); chk("多字段 ⇒ 400", c == 400, c)
        c, b = req(port, "POST", P, raw=b"{not json", token=TOKEN); chk("坏 JSON ⇒ 400", c == 400, c)
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B", "note": "长" * 501}, TOKEN); chk("备注超长 ⇒ 400", c == 400, c)
        c, b = req(port, "POST", P, raw=b"x" * (decisions.MAX_BODY + 1), token=TOKEN); chk("body 超上限 ⇒ 400", c == 400, c)
        c, b = req(port, "POST", "/api/chart?symbol=ZECUSDT&tf=4h", {"id": "S-13", "option": "B"}, TOKEN); chk("别的路径 POST ⇒ 405", c == 405, c)
        c, b = req(port, "POST", P, {"id": "S-13", "option": "B", "note": "照作者原话"}, TOKEN)
        r1 = json.loads(b) if c == 200 else {}
        chk("口令对 ⇒ 200，回存好的那条", c == 200 and r1.get("id") == "S-13" and r1.get("option") == "B" and r1.get("seq") == 1 and r1.get("prev") is None, (c, b))
        c, b = req(port, "POST", P, {"id": "S-13", "option": "A"}, TOKEN)
        r2 = json.loads(b) if c == 200 else {}
        chk("改一条 ⇒ seq 递增、prev 记着上一个", c == 200 and r2.get("seq") == 2 and r2.get("prev") == "B", (c, b))
        c, b = req(port, "GET", P); cur = json.loads(b) if c == 200 else {}
        chk("GET 看得到最新那次", c == 200 and cur.get("S-13", {}).get("option") == "A" and "R-1" not in cur, (c, b))
        with open(decisions.HISTORY, encoding="utf-8") as f:
            hist = [json.loads(x) for x in f]
        chk("历史只追加、两次都在", [(h["id"], h["option"]) for h in hist] == [("S-13", "B"), ("S-13", "A")], hist)
        # 任何错误回包里都不许出现本机路径、口令
        leaks = []
        for body in (req(port, "POST", P, {"id": "S-13", "option": "B"}, "wrong")[1], req(port, "POST", P, raw=b"{", token=TOKEN)[1],
                     req(port, "POST", P, {"id": "S-13", "option": "B"})[1]):
            s = body.decode("utf-8", "replace")
            if tmp in s or TOKEN in s or os.sep + "state" in s:
                leaks.append(s)
        chk("错误回包不漏路径、口令", not leaks, leaks)
    finally:
        srv.shutdown(); srv.server_close()
        decisions.SPEC, decisions.STATE, decisions.CHOICES, decisions.HISTORY, decisions.TOKEN = saved
        shutil.rmtree(tmp, ignore_errors=True)
    if not quiet:
        print("全部通过" if not bad else "%d 处不过" % len(bad))
    return len(bad)


def self_test():
    """变异：把口令校验整个拿掉（谁都能写）⇒ 主跑那几条「403」必须红。"""
    real = decisions.hmac.compare_digest
    decisions.hmac.compare_digest = lambda a, b: True
    real_tok = decisions._token
    try:
        n = run(quiet=True)
    finally:
        decisions.hmac.compare_digest = real
    ok = n > 0
    print("%s 变异「口令校验拿掉」⇒ 主跑 %d 处不过" % ("✓" if ok else "✗", n))
    decisions._token = real_tok
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (1 if run() else 0))
