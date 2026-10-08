"""Dev studio's server side, loaded by Hyimg's server (manifest.json "server"). An HTML file of the library is kind "html" (manifest "kinds"):
its picture for the library's grid and the board's card at rest is the page drawn by Chromium at 1280 × 800 css px, its first screen with
its scripts run (render.py, a process of its own, as Hyimg's HTML stills). Hyimg keeps the picture with its thumbnails, per version of the
file, never beside the page; without Playwright it falls back to Quick Look (the page without its scripts).

Dev mode edits the file (0.2, owner 2026-10-07: «Чтобы я как в Figma мог работать с нашими HTML-файлами»), served at POST
/api/plugin/<plugin>/<route>; the board's own pages call them (Hyimg refuses a write from a sandboxed page, its Origin is null):
  source {p}                     → {rev, html, vars}: the file's revision (sha1), its source with each start tag marked by its place for
                                   the page's parser (htmledit.annotate), its custom properties
  edit {p, rev, ops, session}    → {rev, html, vars, step}: the ops written in place (htmledit.apply), refused (409) when the file is not
                                   at rev any more; the first write of a session keeps a copy of the file in the board's history first
  undo {p, step, dir}            → {rev, html, vars}: a step taken back ("undo") or made again ("redo"), only when the file is still as
                                   that step left it
Only a file of the library: a relative path without .., ending in .html or .htm, a regular file inside the library and outside the board's
state folder, at most 8 MB. Nothing else is ever written."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
MAX = 8 * 1024 * 1024
STEPS_MAX, STEPS_BYTES = 400, 96 * 1024 * 1024


# The picture is drawn at twice the page's css size, 2560 × 1600 (owner 2026-10-08: «справа мазня»: a card at 153 % on a Retina screen
# needs 2200 device px, a 1280 picture was blown up); /thumb hands it out at 640, 1280 or 2560 px as the card's size on screen asks.
# PREVIEW_KEY is part of the name Hyimg keeps the picture under (server.py preview), so the 1280 ones drawn before are drawn again, once,
# when a card first asks for 2560.
PREVIEW_KEY = "2x"


def preview(full, out):
    preview_at(full, out, 1280, 800)


# a card's own viewport (owner 2026-10-08: a 1440 × 900 card's still drawn at 1280 shifted its text and layout when the live page faded
# in): Hyimg's /thumb?…&vw=&vh= asks for it and keeps it apart from the 1280 × 800 one of the library's grid
def preview_at(full, out, w, h):
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"), pathlib.Path(full).as_uri(), str(int(w)), str(int(h)), out, "2"],
                   capture_output=True, timeout=60)


def _edit_mod():   # htmledit.py beside this file, loaded by its path (Hyimg loads this module under a name of its own)
    import importlib.util
    full = os.path.join(HERE, "htmledit.py"); key = os.path.getmtime(full)
    mod = sys.modules.get("hyimg_dev_htmledit")
    if mod is None or getattr(mod, "_MTIME", None) != key:
        spec = importlib.util.spec_from_file_location("hyimg_dev_htmledit", full)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod._MTIME = key
        sys.modules["hyimg_dev_htmledit"] = mod
    return mod


def _library():
    return os.environ.get("HYIMG_LIBRARY_ROOT") or getattr(sys.modules.get("config"), "W", None)   # the server's library (config.py)


def _state():
    return os.environ.get("HYIMG_STATE_ROOT") or getattr(sys.modules.get("config"), "HERE", None)   # the board's state folder


class Bad(ValueError):
    pass


def page_path(rel):
    """the full path of a library HTML file the edits may write, else Bad with the reason"""
    lib = _library()
    if not lib: raise Bad("no library")
    if not isinstance(rel, str) or not rel or "\0" in rel or rel.startswith(("/", "~", "\\")) or ".." in rel.replace("\\", "/").split("/"):
        raise Bad("not a path of the library")
    if not rel.lower().endswith((".html", ".htm")): raise Bad("only .html and .htm files")
    root = os.path.realpath(lib); full = os.path.realpath(os.path.join(root, rel))
    if not full.startswith(root + os.sep): raise Bad("outside the library")
    st = _state()
    if st and (full + os.sep).startswith(os.path.realpath(st) + os.sep): raise Bad("inside the board's own folder")
    if not os.path.isfile(full): raise Bad("no such file")
    if os.path.getsize(full) > MAX: raise Bad("the file is over 8 MB")
    return full


def _json(code, obj):
    return code, "application/json", json.dumps(obj, ensure_ascii=False).encode()


def _req(body):
    try: d = json.loads(body or b"{}")
    except ValueError: raise Bad("bad json")
    if not isinstance(d, dict): raise Bad("bad json")
    return d


def _payload(data):
    H = _edit_mod(); text = H.decode(data); sc = H.scan(text)
    return {"rev": H.rev(data), "html": H.annotate(text, sc), "vars": H.vars_of(text, sc), "size": len(data)}


_LOCK = threading.Lock()
_STEPS = OrderedDict()   # step id -> (full path, library path, bytes before, bytes after): undo and redo while the server runs
_KEPT = set()            # (full path, session): the copy before a session's first write is made


def _write(full, data):
    """the file's new bytes in one move (a reader never sees half of it), its mode kept; its time a second on at least, so the picture's
    cache (keyed by the whole second) draws the page again"""
    old = os.stat(full)
    tmp = os.path.join(os.path.dirname(full), f".{os.path.basename(full)}.hy-{uuid.uuid4().hex[:8]}")
    with open(tmp, "wb") as f: f.write(data)
    shutil.copymode(full, tmp); os.replace(tmp, full)
    if int(os.stat(full).st_mtime) <= int(old.st_mtime):
        os.utime(full, (old.st_atime, int(old.st_mtime) + 1))


def _by(query):
    b = (query or {}).get("_by") or [None]
    return b[0] if isinstance(b[0], dict) else None


def _log(rel, query):
    people = sys.modules.get("people"); st = _state()
    if people and st and hasattr(people, "log_write"):
        try: people.log_write(st, "html", rel, _by(query))
        except OSError: pass


def keep_copy(full, rel, data, session, query):
    """the file as it was before a session's first write: <state>/boards/_history/_html/<library path>/<time>.html, listed in index.jsonl"""
    st = _state()
    if not st or (full, session) in _KEPT: return None
    d = os.path.join(st, "boards", "_history", "_html", *rel.split("/"))
    os.makedirs(d, exist_ok=True)
    name = time.strftime("%y%m%d-%H%M%S") + os.path.splitext(full)[1]; n = 2
    while os.path.exists(os.path.join(d, name)): name = f"{time.strftime('%y%m%d-%H%M%S')}~{n}{os.path.splitext(full)[1]}"; n += 1
    with open(os.path.join(d, name), "wb") as f: f.write(data)
    line = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "path": rel, "copy": "/".join(rel.split("/") + [name]), "label": "before Dev Studio edits"}
    if _by(query): line["by"] = _by(query)
    with open(os.path.join(st, "boards", "_history", "_html", "index.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    _KEPT.add((full, session))
    return line["copy"]


def _step(full, rel, before, after):
    sid = uuid.uuid4().hex[:12]
    _STEPS[sid] = (full, rel, before, after)
    while len(_STEPS) > STEPS_MAX or sum(len(b) + len(a) for _f, _r, b, a in _STEPS.values()) > STEPS_BYTES:
        _STEPS.popitem(last=False)
    return sid


def source(body=b"", query=None):
    try:
        full = page_path(_req(body).get("p"))
        with open(full, "rb") as f: return _json(200, _payload(f.read()))
    except Bad as ex: return _json(400, {"error": str(ex)})


def edit(body=b"", query=None):
    try:
        req = _req(body); rel = req.get("p"); full = page_path(rel)
    except Bad as ex: return _json(400, {"error": str(ex)})
    H = _edit_mod()
    with _LOCK:
        with open(full, "rb") as f: data = f.read()
        if H.rev(data) != req.get("rev"): return _json(409, {"error": "the file changed since the page read it", "stale": True})
        try: new = H.encode(H.apply(H.decode(data), req.get("ops")))
        except H.Refused as ex: return _json(422, {"error": str(ex)})
        if new == data: return _json(200, {**_payload(data), "step": None})
        copy = keep_copy(full, rel, data, str(req.get("session") or "")[:40], query)
        _write(full, new)
        sid = _step(full, rel, data, new)
    _log(rel, query)
    return _json(200, {**_payload(new), "step": sid, "copy": copy})


def undo(body=b"", query=None):
    try:
        req = _req(body); rel = req.get("p"); full = page_path(rel)
    except Bad as ex: return _json(400, {"error": str(ex)})
    with _LOCK:
        st = _STEPS.get(str(req.get("step") or ""))
        if not st or st[0] != full: return _json(410, {"error": "that step is gone: the server started again"})
        back = req.get("dir") != "redo"
        want, put = (st[3], st[2]) if back else (st[2], st[3])
        with open(full, "rb") as f: data = f.read()
        if data != want: return _json(409, {"error": "the file changed since that step", "stale": True})
        _write(full, put)
    _log(rel, query)
    return _json(200, _payload(put))


ROUTES = {"source": source, "edit": edit, "undo": undo}
