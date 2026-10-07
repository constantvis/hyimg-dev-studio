"""Dev mode edits the HTML file (0.2, owner 2026-10-07: «Почему мы используем картинки, а не реальный HTML? Я смогу два раза нажать на них и
поменять там цвет ... Чтобы я как в Figma мог работать с нашими HTML-файлами»). On a disposable library, Chromium, the dark theme:

- a click selects an element; a fill typed in the inspector lands in its style attribute and nothing else of the file changes, byte for byte
- a value from a custom property: «Everywhere» writes the property's :root declaration, and only it
- a double click types a text in place; Enter writes it
- an element made by the page's script is selectable, its controls grey with the reason; a static one next to it maps to its own tag
- ⌘Z takes every write back to the file's first bytes, ⇧⌘Z makes one again; the first write kept a copy in the board's history
- the write route takes only .html and .htm of the library and only Dev mode's edits; a sandboxed page (Origin null) can't call it

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_edit.py
  HYIMG_SHOTS=<folder> saves the screenshots
"""
import json, os, subprocess, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import REPO, HERE, free_port

SHOTS = os.environ.get("HYIMG_SHOTS")
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Edit fixture</title>
<style>
  :root { --purple: #7c3aed; --ink: #111827; }
  body { margin: 0; font: 16px system-ui; color: var(--ink); background: #ffffff; }
  .card { background: var(--purple); color: #fff; padding: 24px; border-radius: 12px; margin: 24px; }
  .tag { border: 2px solid var(--purple); color: var(--purple); padding: 4px 8px; background: #fff; }
</style>
</head>
<body>
  <header id="top"><h1 id="title">Hello world</h1></header>
  <main>
    <section class="card" id="hero"><p id="lead">Some text</p><span class="tag">New</span></section>
    <ul id="list"><li>One</li><li>Two</li></ul>
  </main>
  <div id="made"></div>
  <script>
    const d = document.createElement('div'); d.id = 'dyn'; d.className = 'card'; d.textContent = 'Made by a script';
    document.getElementById('made').appendChild(d);
    const li = document.createElement('li'); li.textContent = 'Zero'; document.getElementById('list').prepend(li);
  </script>
</body>
</html>
"""


@pytest.fixture
def ed(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": "en", "cv.theme": "dark"}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/edit.html").write_bytes(PAGE.encode())
    (lib / "site/style.css").write_text("body{}")
    (tmp_path / "secret.html").write_text("<p>outside the library</p>")
    (plugins / "dev").symlink_to(HERE)
    items = {"e1": {"type": "html", "src": "site/edit.html", "vw": 1280, "x": 0, "y": 0, "w": 640, "h": 400, "pics": ["site/edit.html"]}}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 1, "items": items, "groups": {}, "removed": {}}))
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HYIMG_", "REVIEW_"))}
    (tmp_path / "home").mkdir()
    env.update(HOME=str(tmp_path / "home"), PLAYWRIGHT_BROWSERS_PATH=os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(Path.home() / "Library/Caches/ms-playwright"))
    env.update(HYIMG_LIBRARY_ROOT=str(lib), HYIMG_STATE_ROOT=str(state), HYIMG_PROJECT_ID=str(uuid.uuid4()), HYIMG_PLUGINS=str(plugins),
               HYIMG_SETTINGS=str(tmp_path / "settings.json"), PYTHONDONTWRITEBYTECODE="1", HY_TEST_ONLY_PLUGINS="1")
    log = open(tmp_path / "server.log", "w+")
    proc = subprocess.Popen([sys.executable, str(REPO / "review/server.py"), str(port)], env=env, stdout=log, stderr=log)
    for _ in range(100):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); break
        except OSError: time.sleep(0.1)
    try:
        yield port, lib, state, tmp_path
    finally:
        proc.terminate(); proc.wait(5); log.close()


def post(port, route, body, headers=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/plugin/dev/{route}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw or b"{}")
        except ValueError: return e.code, {"raw": raw[:200]}


def file_is(path, want, t=8):
    end = time.time() + t
    while True:
        have = path.read_bytes()
        if have == want: return
        if time.time() > end: raise AssertionError(f"the file:\n{have.decode()}\n\nwanted:\n{want.decode()}")
        time.sleep(0.1)


def splice(text, after, add):
    """the text with add put right after the first occurrence of `after`"""
    k = text.index(after) + len(after)
    return text[:k] + add + text[k:]


def shot(page, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name))


def click_in(page, frame, sel, dbl=False, shift=False):
    """a press on an element of the page, through the select tool's catcher"""
    box = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
    x, y = frame.evaluate(f"(() => {{ const r = document.querySelector({json.dumps(sel)}).getBoundingClientRect(); return [r.left + Math.min(20, r.width / 2), r.top + r.height / 2] }})()")
    s = box["width"] / 1280
    page.mouse.move(box["x"] + x * s, box["y"] + y * s); page.wait_for_timeout(60)
    if shift: page.keyboard.down("Shift")
    (page.mouse.dblclick if dbl else page.mouse.click)(box["x"] + x * s, box["y"] + y * s)
    if shift: page.keyboard.up("Shift")


def picked(page, tag, text=None):
    try: return _picked(page, tag, text)
    except Exception:
        raise AssertionError(json.dumps(page.evaluate("""({ d: __dev.D && __dev.D.detail && { t: __dev.D.detail.t, src: __dev.D.detail.src },
          rev: __dev.D && __dev.D.rev, err: __dev.D && __dev.D.srcErr })""")))


def _picked(page, tag, text=None):
    page.wait_for_function(f"""() => {{ const d = __dev.D && __dev.D.detail; return d && d.t === {json.dumps(tag)} && d.src && d.src.why !== 'wait'
      && (d.src.why || d.src.rev === __dev.D.rev) {f"&& d.src.text === {json.dumps(text)}" if text else ""} }}""", timeout=8000)
    return page.evaluate("__dev.D.detail")


def test_edits_write_the_file_in_place_and_undo_takes_them_back(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br = p.chromium.launch(); page = br.new_page(viewport={"width": 1500, "height": 950}, color_scheme="dark")
        errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        page.dblclick(".plg[data-id=e1]")
        page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.rev", timeout=20000)
        frame = next(fr for fr in page.frames if "/sandbox/" in fr.url)
        frame.wait_for_function("() => document.getElementById('dyn')")
        last = None
        for _ in range(40):   # the camera's flight between the panels has ended
            page.wait_for_timeout(150); b = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
            if b == last: break
            last = b
        assert page.evaluate("__dev.D.picking") is True, "the select tool is on when Dev mode opens"

        # 1. a click selects the h1; a fill typed in the inspector goes into its style attribute, nothing else of the file changes
        click_in(page, frame, "#title"); d = picked(page, "h1", "Hello world")
        assert d["src"]["at"] == PAGE.index('<h1 id="title">')
        page.fill(".dvr input[data-c='background-color']", "#ff0000"); page.press(".dvr input[data-c='background-color']", "Enter")
        want1 = splice(PAGE, '<h1 id="title"', ' style="background-color: #ff0000"').encode()
        file_is(f, want1)
        assert frame.evaluate("getComputedStyle(document.getElementById('title')).backgroundColor") == "rgb(255, 0, 0)"
        copies = list((state / "boards/_history/_html/site/edit.html").glob("*.html"))
        assert len(copies) == 1 and copies[0].read_bytes() == orig, "the file as it was, kept before the first write"
        line = json.loads((state / "boards/_history/_html/index.jsonl").read_text().splitlines()[-1])
        assert line["path"] == "site/edit.html" and line["label"] == "before Dev mode edits"

        # 2. the section's fill comes from --purple: the inspector says so; «Everywhere» writes the :root declaration only
        click_in(page, frame, "#hero", shift=False); page.mouse.move(5, 5)
        d = picked(page, "section")
        assert d["ed"]["p"]["background-color"]["var"] == "--purple"
        page.wait_for_selector(".dvr .dcr[data-p='background-color'] .dvar:text-is('--purple')")
        assert "Everywhere · 3" in page.inner_text(".dvr hy-segmented[data-s='background-color']")
        shot(page, "dev-edit-var-dark.png")
        page.click(".dvr hy-segmented[data-s='background-color'] button[value=all]")
        page.wait_for_function("() => __dev.D.scope['background-color'] === 'all'")
        page.fill(".dvr input[data-c='background-color']", "#00aa00"); page.press(".dvr input[data-c='background-color']", "Enter")
        want2 = want1.decode().replace("--purple: #7c3aed;", "--purple: #00aa00;").encode()
        file_is(f, want2)
        assert frame.evaluate("getComputedStyle(document.querySelector('.tag')).borderTopColor") == "rgb(0, 170, 0)", "every use follows, live"

        # 3. a double click on a text types it in place; Enter writes it
        click_in(page, frame, "#lead", dbl=True)
        frame.wait_for_function("() => document.getElementById('lead').isContentEditable")
        page.keyboard.type("New text"); shot(page, "dev-edit-typing-dark.png"); page.keyboard.press("Enter")
        want3 = want2.decode().replace('<p id="lead">Some text</p>', '<p id="lead">New text</p>').encode()
        file_is(f, want3)
        assert not frame.evaluate("document.getElementById('lead').isContentEditable")

        # 4. a script's element: selectable, its controls grey with the reason; the static li beside the script's one is its own tag
        click_in(page, frame, "#dyn"); d = picked(page, "div")
        assert d["src"] == {"why": "script"}
        assert "Made by a script" in page.inner_text(".dvr .doff")
        assert page.evaluate("[...document.querySelectorAll('.dvr .ded')].every(s => s.inert)")
        shot(page, "dev-edit-script-dark.png")
        click_in(page, frame, "#list li:nth-child(1)"); d = picked(page, "li")
        assert d["src"] == {"why": "script"}, "Zero was put in front by the script"
        click_in(page, frame, "#list li:nth-child(2)"); d = picked(page, "li", "One")
        assert d["src"]["at"] == want3.decode().index("<li>One")
        assert f.read_bytes() == want3

        # 5. ⌘Z takes the three writes back to the first bytes; ⇧⌘Z makes the first one again; the undo button agrees
        page.evaluate("document.activeElement && document.activeElement.blur()")
        for want in (want2, want1, orig):
            page.keyboard.press("Meta+z"); file_is(f, want)
        assert page.evaluate("document.querySelector('.dvbar [data-a=undo]').disabled")
        page.keyboard.press("Meta+Shift+z"); file_is(f, want1)
        page.wait_for_function("() => getComputedStyle(document.querySelector('.plg[data-id=e1] iframe.dvf')) && true")
        frame.wait_for_function("() => getComputedStyle(document.getElementById('title')).backgroundColor === 'rgb(255, 0, 0)'")
        page.click(".dvbar [data-a=undo]"); file_is(f, orig)
        frame.wait_for_function("() => getComputedStyle(document.getElementById('title')).backgroundColor !== 'rgb(255, 0, 0)'")

        # 6. ⇧ adds an element: one weight for both, one write, one step
        click_in(page, frame, "#title"); picked(page, "h1"); click_in(page, frame, "#lead", shift=True)
        page.wait_for_function("() => __dev.D.sels.size === 2 && __dev.D.more.length === 1 && __dev.D.more[0].src.rev === __dev.D.rev")
        assert "2 elements" in page.inner_text(".dvr .ih")
        shot(page, "dev-edit-two-dark.png")
        page.click(".dvr hy-segmented[data-w] button[value='700']")
        two = PAGE.replace('<h1 id="title">', '<h1 id="title" style="font-weight: 700">').replace('<p id="lead">', '<p id="lead" style="font-weight: 700">')
        file_is(f, two.encode())
        page.evaluate("document.activeElement && document.activeElement.blur()"); page.keyboard.press("Meta+z"); file_is(f, orig)

        # Done: the card's picture is asked again for the file's new version
        page.click(".dvbar [data-a=done]"); page.wait_for_function("() => !__dev.D")
        page.wait_for_function("() => /&v=[0-9a-f]{40}$/.test(document.querySelector('.plg[data-id=e1] img.dvi').src)")
        assert not errors, errors
        br.close()


def test_the_write_route_takes_only_html_of_the_library_and_only_edits(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    st, src = post(port, "source", {"p": "site/edit.html"})
    assert st == 200 and src["rev"] and 'data-hy-at="' in src["html"] and {v["name"] for v in src["vars"]} == {"--purple", "--ink"}
    at = PAGE.index('<h1 id="title">')
    ok = {"p": "site/edit.html", "rev": src["rev"], "ops": [{"op": "style", "at": at, "tag": "h1", "set": {"color": "red"}}]}
    for bad, code in [({**ok, "p": "../secret.html"}, 400), ({**ok, "p": "%2e%2e/secret.html"}, 400), ({**ok, "p": str(tmp / "secret.html")}, 400),
                      ({**ok, "p": "site/style.css"}, 400), ({**ok, "p": "site/none.html"}, 400), ({**ok, "rev": "0" * 40}, 409),
                      ({**ok, "ops": [{"op": "write", "data": "x"}]}, 422), ({**ok, "ops": [{"op": "style", "at": at, "tag": "h1", "set": {"position": "fixed"}}]}, 422),
                      ({**ok, "ops": [{"op": "style", "at": at, "tag": "h1", "set": {"color": "red\" onload=\"x"}}]}, 422),
                      ({**ok, "ops": [{"op": "style", "at": at, "tag": "p", "set": {"color": "red"}}]}, 422),
                      ({**ok, "ops": [{"op": "text", "at": at, "tag": "h1", "was": "Something else", "text": "x"}]}, 422)]:
        assert post(port, "edit", bad)[0] == code, bad
    assert f.read_bytes() == orig
    # a sandboxed page has Origin null: Hyimg refuses its write before the route runs
    assert post(port, "edit", ok, {"Origin": "null"})[0] == 403 and f.read_bytes() == orig
    # the route itself: in place, and undo only while the file is as the step left it
    st, res = post(port, "edit", ok)
    assert st == 200 and f.read_bytes() == splice(PAGE, '<h1 id="title"', ' style="color: red"').encode()
    (lib / "site/edit.html").write_bytes(f.read_bytes() + b"<!-- changed outside -->")
    assert post(port, "undo", {"p": "site/edit.html", "step": res["step"], "dir": "undo"})[0] == 409
    assert post(port, "undo", {"p": "site/edit.html", "step": "nope", "dir": "undo"})[0] == 410
