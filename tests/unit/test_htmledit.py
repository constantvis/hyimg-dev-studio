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


# Edit mode (owner 2026-10-09 on round 15: «режим редактирования HTML ... как в браузере в инспекторе»): attributes, a tag's name, an
# element taken out; each changes only its own bytes, and what the file can't say for sure is refused
DOC = """<body>
  <section class="card hero" id=s data-x='a "q"' hidden>
    <h1 id="t">Hello</h1>
    <div class="x"><div>inner</div></div>
    <img src=x.png/>
  </section>
<ul><li>Open<li>Next</li></ul>
<p>One<div>x</div></p>
<svg><path d="M0 0"/></svg>
</body>"""


def d_at(s):
    return DOC.index(s)


def test_attributes_set_add_and_remove_in_place():
    sec = d_at("<section")
    t = H.apply(DOC, [{"op": "attrs", "at": sec, "tag": "section", "set": {"class": "card", "id": "z", "title": 'a&b"c'}, "was": {"class": "card hero", "id": "s"}}])
    assert t == DOC.replace("""<section class="card hero" id=s data-x='a "q"' hidden>""", """<section class="card" id="z" data-x='a "q"' hidden title="a&amp;b&quot;c">""")
    t = H.apply(DOC, [{"op": "attrs", "at": sec, "tag": "section", "set": {"data-x": "it's", "hidden": None}}])
    assert t == DOC.replace("""data-x='a "q"' hidden>""", "data-x='it&#39;s'>"), "the value in its own quotes, the attribute with its space gone"
    t = H.apply(DOC, [{"op": "attrs", "at": d_at("<img"), "tag": "img", "set": {"alt": "x"}}])
    assert t == DOC.replace("<img src=x.png/>", '<img src=x.png/ alt="x">'), "the slash of an unquoted value stays its own"
    t = H.apply(DOC, [{"op": "attrs", "at": d_at("<path"), "tag": "path", "set": {"fill": "red"}}])
    assert t == DOC.replace('<path d="M0 0"/>', '<path d="M0 0" fill="red"/>')
    assert H.apply(DOC, [{"op": "attrs", "at": sec, "tag": "section", "set": {"class": "card hero"}}]) == DOC, "the same value writes nothing"


def test_rename_and_remove_take_the_end_tag_and_the_line():
    x = d_at('<div class="x">')
    t = H.apply(DOC, [{"op": "tag", "at": x, "tag": "div", "name": "article", "inner": 1}])
    assert t == DOC.replace('<div class="x"><div>inner</div></div>', '<article class="x"><div>inner</div></article>'), "the nested div's end tag is its own"
    t = H.apply(DOC, [{"op": "remove", "at": x, "tag": "div", "inner": 1}])
    assert t == DOC.replace('    <div class="x"><div>inner</div></div>\n', ""), "alone on its line: the line goes"
    t = H.apply(DOC, [{"op": "remove", "at": d_at("<li>Next"), "tag": "li", "inner": 0}])
    assert t == DOC.replace("<li>Next</li>", ""), "beside others on its line: only the element"
    assert H.apply(DOC, [{"op": "remove", "at": d_at("<img"), "tag": "img"}]) == DOC.replace("    <img src=x.png/>\n", "")


@pytest.mark.parametrize("op", [
    {"op": "remove", "at": DOC.index("<li>Open"), "tag": "li", "inner": 0},      # its end tag is left out
    {"op": "remove", "at": DOC.index("<p>"), "tag": "p", "inner": 0},            # the browser closes it before the div
    {"op": "tag", "at": DOC.index('<div class="x">'), "tag": "div", "name": "p", "inner": 0},   # not the page's count inside
    {"op": "tag", "at": DOC.index("<body"), "tag": "body", "name": "main"},
    {"op": "remove", "at": DOC.index("<body"), "tag": "body"},
    {"op": "tag", "at": DOC.index("<h1"), "tag": "h1", "name": "script", "inner": 0},
    {"op": "tag", "at": DOC.index("<h1"), "tag": "h1", "name": "h1 onclick=x", "inner": 0},
    {"op": "attrs", "at": DOC.index("<h1"), "tag": "h1", "set": {"data-hy-at": "1"}},
    {"op": "attrs", "at": DOC.index("<h1"), "tag": "h1", "set": {"a b": "1"}},
    {"op": "attrs", "at": DOC.index("<h1"), "tag": "h1", "set": {"id": "x"}, "was": {"id": "other"}},   # a script changed it
    {"op": "attrs", "at": DOC.index("<h1"), "tag": "h2", "set": {"id": "x"}},
    {"op": "attrs", "at": DOC.index("<h1"), "tag": "h1", "set": {"id": "a\x00b"}},
])
def test_what_edit_mode_cant_be_sure_of_is_refused(op):
    with pytest.raises(H.Refused):
        H.apply(DOC, [op])
