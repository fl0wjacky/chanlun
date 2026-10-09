# -*- coding: utf-8 -*-
"""决策树网页的后端（card-fe3aebd3-819，小栋 10-09 11:10）：给数据、存小栋的选择。

数据：状态目录里有 decisions.json 就用它（Nova 审过一批，Bram 从 Atlas 的数据支同步过去，不用等合 main）；
      没有就用仓库里的 docs/spec/decisions.json（Atlas 维护，字段见那份文件）。每次请求现读，不用重启。
选择：存在**仓库外**的状态目录里，默认是「这份 checkout 旁边」的 .chanlun-state/（跟仓库同级，不在仓库里）；
      要换位置设环境变量 CHANLUN_STATE_DIR。目录、口令都不进仓库、不进页面。
  · decisions-choices.json   当前每条的选择 {id: {option, note, at, seq}}，原子写（临时文件 + rename）
  · decisions-choices.jsonl  只追加的历史，一行一次保存（谁改了什么、什么时候），推翻过的也留着
  · decisions.token          口令，一行，**只用 ASCII**（HTTP 头放不下中文）。没有这个文件 ⇒ 写接口一律 503（没配置），不是「谁都能写」
写接口要带 X-Decision-Token，跟文件里的口令常数时间比较；错了 403，并在本机日志记一行（不记口令本身）。
"""
import hmac
import json
import os
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "docs", "spec", "decisions.json")
STATE = os.environ.get("CHANLUN_STATE_DIR") or os.path.join(os.path.dirname(ROOT), ".chanlun-state")
SPEC_LIVE = os.path.join(STATE, "decisions.json")   # 有就优先：审过的最新一批
CHOICES = os.path.join(STATE, "decisions-choices.json")
HISTORY = os.path.join(STATE, "decisions-choices.jsonl")
TOKEN = os.path.join(STATE, "decisions.token")
MAX_BODY = 4096                       # 一次选择的 body 上限（字节）
MAX_NOTE = 500                        # 备注上限（字）
_lock = threading.Lock()


class Bad(Exception):
    """调用方的错：code 是 HTTP 状态码，msg 是给前端看的固定措辞（不带路径、不带内部原因）。"""
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def spec_bytes():
    """→ decisions.json 原样字节：状态目录那份优先，没有就用仓库那份；两份都不在 ⇒ None（接口回 503）。"""
    for p in (SPEC_LIVE, SPEC):
        try:
            with open(p, "rb") as f:
                return f.read()
        except FileNotFoundError:
            continue
    return None


def _items():
    raw = spec_bytes()
    if raw is None:
        raise Bad(503, "decisions not available")
    d = json.loads(raw)
    items = d if isinstance(d, list) else d.get("items") or d.get("decisions") or []
    return {x["id"]: x for x in items if isinstance(x, dict) and "id" in x}


def choices():
    """→ {id: {option, note, at, seq}}；还没人选过 ⇒ {}。"""
    try:
        with open(CHOICES, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _token():
    try:
        with open(TOKEN, encoding="utf-8") as f:
            t = f.read().strip()
        return t or None
    except FileNotFoundError:
        return None


def save(body, token):
    """body：请求体字节；token：X-Decision-Token 头。→ 存好的那一条 dict（含 id）。错了抛 Bad。"""
    want = _token()
    if want is None:
        raise Bad(503, "saving not configured")
    if not token or not hmac.compare_digest(token.encode("utf-8"), want.encode("utf-8")):
        raise Bad(403, "bad token")
    if len(body) > MAX_BODY:
        raise Bad(400, "body too large")
    try:
        req = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise Bad(400, "bad json")
    if not isinstance(req, dict) or not set(req) <= {"id", "option", "note"} or not {"id", "option"} <= set(req):
        raise Bad(400, "fields: id, option, note?")
    did, opt, note = req["id"], req["option"], req.get("note", "")
    if not all(isinstance(x, str) for x in (did, opt, note)) or len(note) > MAX_NOTE:
        raise Bad(400, "bad field")
    item = _items().get(did)
    if item is None:
        raise Bad(400, "unknown id")
    keys = {o.get("key") for o in item.get("options", []) if isinstance(o, dict)}
    if opt not in keys:
        raise Bad(400, "unknown option")
    with _lock:
        cur = choices()
        seq = 1 + max((v.get("seq", 0) for v in cur.values()), default=0)
        rec = dict(option=opt, note=note, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), seq=seq,
                   prev=cur.get(did, {}).get("option"))
        cur[did] = rec
        os.makedirs(STATE, exist_ok=True)
        tmp = CHOICES + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, CHOICES)
        with open(HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(rec, id=did), ensure_ascii=False) + "\n")
    return dict(rec, id=did)
