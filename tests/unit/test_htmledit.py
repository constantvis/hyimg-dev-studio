"""htmledit.py and the routes in server.py on a temporary library: each edit changes only its own bytes, what is not an edit Dev mode
makes is refused, the routes take only .html and .htm files of the library. No browser, no server."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("hyimg_dev_htmledit_unit", ROOT / "htmledit.py")
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)

SRC = """<!doctype html><html><head><title>A <b> page</title><style>
  :root { --purple: #7c3aed; --ink:#111 }
  @media (prefers-color-scheme: dark) { :root { --purple: #a78bfa; } }
  .card { background: var(--purple); border: 1px solid var(--purple) }
</style></head><body><h1 id="t">Hello &amp; welcome</h1><p style="margin:0">Text <b>bold</b></p><br/><img src=x.png/>
<li>Open item<li>Next</body></html>"""


def at(s, i=0):
    return SRC.index(s) + i


def test_annotate_marks_each_start_tag_and_nothing_inside_raw_text():
    out = H.annotate(SRC)
    assert f'<h1 id="t" data-hy-at="{at("<h1")}">' in out and f'<br/ data-hy-at="{at("<br")}">' in out
    assert "<title data-hy-at=" in out and "<b> page</title>" in out, "a title's text is not markup"
    assert out.replace(" data-hy-at=", "").count("data-hy-at") == 0 and len(out) > len(SRC)


def test_a_style_change_is_the_only_change():
    t = H.apply(SRC, [{"op": "style", "at": at("<h1"), "tag": "h1", "set": {"color": "#ff0000"}}])
    assert t == SRC.replace('<h1 id="t">', '<h1 id="t" style="color: #ff0000">')
    t = H.apply(SRC, [{"op": "style", "at": at("<p "), "tag": "p", "set": {"color": "red", "padding": "4px 8px"}}])
    assert t == SRC.replace('style="margin:0"', 'style="margin:0; color: red; padding: 4px 8px"')
    t = H.apply(t, [{"op": "style", "at": at("<p "), "tag": "p", "set": {"color": "blue", "padding": ""}}])
    assert t == SRC.replace('style="margin:0"', 'style="margin:0; color: blue"')
    h1 = H.apply(SRC, [{"op": "style", "at": at("<h1"), "tag": "h1", "set": {"color": "red"}}])
    assert H.apply(h1, [{"op": "style", "at": at("<h1"), "tag": "h1", "set": {"color": ""}}]) == SRC, "the last property takes the attribute"
    assert H.apply(SRC, [{"op": "style", "at": at("<br"), "tag": "br", "set": {"opacity": "0.5"}}]) == SRC.replace("<br/>", '<br style="opacity: 0.5"/>')


def test_text_and_var_edits():
    t = H.apply(SRC, [{"op": "text", "at": at("<h1"), "tag": "h1", "was": "Hello & welcome", "text": "Hi <there>"}])
    assert t == SRC.replace("Hello &amp; welcome", "Hi &lt;there&gt;")
    t = H.apply(SRC, [{"op": "text", "at": at("<li>"), "tag": "li", "was": "Open item", "text": "Item"}])
    assert t == SRC.replace("<li>Open item<li>", "<li>Item<li>"), "an li whose end tag is left out"
    t = H.apply(SRC, [{"op": "var", "name": "--purple", "value": "#00aa00"}])
    assert t == SRC.replace("--purple: #7c3aed;", "--purple: #00aa00;")
    v = {x["name"]: x for x in H.vars_of(SRC)}
    assert v["--purple"] == {"name": "--purple", "value": "#7c3aed", "where": "root", "uses": 2} and v["--ink"]["uses"] == 0


@pytest.mark.parametrize("op", [
    {"op": "style", "at": 0, "tag": "h1", "set": {"color": "red"}},
    {"op": "style", "at": SRC.index("<h1"), "tag": "p", "set": {"color": "red"}},
    {"op": "style", "at": SRC.index("<h1"), "tag": "h1", "set": {"position": "fixed"}},
    {"op": "style", "at": SRC.index("<h1"), "tag": "h1", "set": {"color": "red;background:url(x)"}},
    {"op": "style", "at": SRC.index("<h1"), "tag": "h1", "set": {"color": 'red" onclick="x'}},
    {"op": "style", "at": SRC.index("<h1"), "tag": "h1", "set": {"color": "</style><script>"}},
    {"op": "text", "at": SRC.index("<p "), "tag": "p", "was": "Text bold", "text": "x"},
    {"op": "text", "at": SRC.index("<h1"), "tag": "h1", "was": "Another", "text": "x"},
    {"op": "var", "name": "--nope", "value": "1"},
    {"op": "var", "name": "--purple", "value": "red; } body { x: y"},
    {"op": "write", "path": "/etc/passwd", "data": "x"},
])
def test_what_is_not_an_edit_is_refused(op):
    with pytest.raises(H.Refused):
        H.apply(SRC, [op])


def test_routes_refuse_paths_outside_and_files_not_html(server, tmp_path, monkeypatch):
    lib = tmp_path / "lib"; (lib / "site").mkdir(parents=True); (lib / "site/a.html").write_text(SRC); (lib / "site/a.css").write_text("x")
    (tmp_path / "out.html").write_text(SRC); (lib / "link.html").symlink_to(tmp_path / "out.html")
    monkeypatch.setenv("HYIMG_LIBRARY_ROOT", str(lib)); monkeypatch.setenv("HYIMG_STATE_ROOT", str(tmp_path / "state"))
    call = lambda fn, body: (lambda r: (r[0], json.loads(r[2])))(fn(json.dumps(body).encode(), {}))
    for p in ("../out.html", "/etc/hosts", "site/a.css", "link.html", "site/none.html", "", None, "site/../../out.html"):
        assert call(server.source, {"p": p})[0] == 400, p
    st, src = call(server.source, {"p": "site/a.html"})
    assert st == 200
    st, res = call(server.edit, {"p": "site/a.html", "rev": src["rev"], "session": "s1",
                                 "ops": [{"op": "style", "at": at("<h1"), "tag": "h1", "set": {"color": "red"}}]})
    assert st == 200 and (lib / "site/a.html").read_text() == SRC.replace('<h1 id="t">', '<h1 id="t" style="color: red">')
    assert (tmp_path / "state/boards/_history/_html/site/a.html").is_dir()
    assert call(server.undo, {"p": "site/a.html", "step": res["step"], "dir": "undo"})[0] == 200 and (lib / "site/a.html").read_text() == SRC
    assert call(server.undo, {"p": "site/a.html", "step": res["step"], "dir": "redo"})[0] == 200
    assert call(server.undo, {"p": "site/a.html", "step": res["step"], "dir": "redo"})[0] == 409, "redo twice: the file is not as before"
