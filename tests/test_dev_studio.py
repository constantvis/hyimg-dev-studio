"""Dev studio on a real board, a disposable library (owner 2026-10-06: «Board, Image, Dev, 3D» in the dock; «Dev mode is for HTML, on the left
the HTML tree»). The plugins sit side by side in one folder: HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_studio.py
The board loads this plugin with the frames and 3D plugins (their modes are in the same switch); nothing of the owner's is touched."""
import io, json, os, socket, subprocess, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent
REPOS = HERE.parent
REPO = Path(os.environ.get("HYIMG_REPO", REPOS / "hyimg"))
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Demo shop</title><link rel="stylesheet" href="style.css"></head>
<body><header id="top" class="bar dark"><nav><a href="#a">Home</a><a href="#b">Shop</a></nav></header>
<main class="grid"><section class="card hero"><h1 id="t">Hello</h1><p>Some text</p><button id="b">Press</button></section>
<section class="card"><ul><li>One</li><li>Two</li></ul></section></main>
<script>document.getElementById('b').onclick = () => { const li = document.createElement('li'); li.textContent = 'New'; document.querySelector('ul').appendChild(li); };
try { document.body.dataset.parent = String(window.parent.document.title); } catch (e) { document.body.dataset.parent = 'blocked'; }
try { localStorage.setItem('x', '1'); document.body.dataset.storage = 'open'; } catch (e) { document.body.dataset.storage = 'blocked'; }</script>
<script type="module">import { v } from './mod.js'; document.body.dataset.mod = v;</script></body></html>"""
CSS = "body{margin:0;font:16px system-ui;background:rgb(10,120,200);color:#fff} .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;padding:24px} h1{font-size:48px;margin:0 0 8px}"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def png(c):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (400, 600), c).save(b, "PNG"); return b.getvalue()


@pytest.fixture
def hy(tmp_path, request):
    lang = getattr(request, "param", "en")
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": lang}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", lib / "a", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/index.html").write_text(PAGE); (lib / "site/style.css").write_text(CSS); (lib / "site/mod.js").write_text("export const v = 'yes';")
    (lib / "site/about.htm").write_text("<html><body><h2>About</h2></body></html>")
    (tmp_path / "secret.txt").write_text("outside the library")
    for n, c in enumerate([(200, 80, 80), (80, 160, 90)]): (lib / "a" / f"{n}.png").write_bytes(png(c))
    (plugins / "dev").symlink_to(HERE)
    for n, repo in (("frames", "hyimg-frames"), ("3d", "hyimg-3d-studio")):
        if (REPOS / repo / "manifest.json").is_file(): (plugins / n).symlink_to(REPOS / repo)
    items = {"i0": {"path": "a/0.png", "x": 0, "y": 0, "w": 200, "ar": 2 / 3, "crop": None},
             "i1": {"path": "a/1.png", "x": 240, "y": 0, "w": 200, "ar": 2 / 3, "crop": None},
             "h1": {"type": "html", "src": "site/index.html", "vw": 1280, "x": 0, "y": 400, "w": 640, "h": 400, "pics": ["site/index.html"]},
             "m1": {"type": "model3d", "empty": True, "x": 700, "y": 400, "w": 400, "h": 300}}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 1, "items": items, "groups": {}, "removed": {}}))
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HYIMG_", "REVIEW_"))}
    # a home of its own: the plugins in the real ~/Library/Application Support/Hyimg/plugins stay out; Chromium for the pages' pictures stays found
    (tmp_path / "home").mkdir()
    env.update(HOME=str(tmp_path / "home"), PLAYWRIGHT_BROWSERS_PATH=os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(Path.home() / "Library/Caches/ms-playwright"))
    env.update(HYIMG_LIBRARY_ROOT=str(lib), HYIMG_STATE_ROOT=str(state), HYIMG_PROJECT_ID=str(uuid.uuid4()), HYIMG_PLUGINS=str(plugins),
               HYIMG_SETTINGS=str(tmp_path / "settings.json"), PYTHONDONTWRITEBYTECODE="1")
    log = open(tmp_path / "server.log", "w+")
    proc = subprocess.Popen([sys.executable, str(REPO / "review/server.py"), str(port)], env=env, stdout=log, stderr=log)
    for _ in range(100):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); break
        except OSError: time.sleep(0.1)
    try:   # the server goes even when the test fails or is interrupted
        yield port, lib, state
    finally:
        proc.terminate(); proc.wait(5); log.close()


def get(port, path, headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def board(p, port, browser="chromium", size=(1400, 900)):
    br = getattr(p, browser).launch()
    page = br.new_page(viewport={"width": size[0], "height": size[1]})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    n = len(json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/plugins").read()))
    page.wait_for_function(f"() => typeof PLGST !== 'undefined' && PLGST.length === {n} && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
    return br, page, errors


def modes(page):
    return page.evaluate("Object.fromEntries([...document.querySelectorAll('#modes > button')].map(b => [b.dataset.mode, "
                         "(b.getAttribute('aria-pressed') === 'true' ? 'on' : b.getAttribute('aria-disabled') === 'true' ? 'off' : 'can')]))")


def pick(page, ids):
    page.evaluate(f"(() => {{ sel = new Set({json.dumps(ids)}); render(); }})()"); page.wait_for_timeout(120)


def test_library_lists_html_and_serves_it_sandboxed_and_read_only(hy):
    port, lib, state = hy
    items = json.loads(get(port, "/api/items")[2])
    kinds = {i["path"]: (i.get("kind"), i.get("ext")) for i in items}
    assert kinds["site/index.html"] == ("html", "HTML") and kinds["site/about.htm"] == ("html", "HTM") and kinds["a/0.png"] == (None, None)
    base = json.loads(get(port, "/api/sandbox")[2])["base"]
    assert base.startswith("/sandbox/") and len(base) > 20
    # the page: CSP sandbox, no inspector unless asked, its css by a relative link; a font or module request with Origin null gets CORS
    st, h, body = get(port, base + "site/index.html")
    assert st == 200 and h["Content-Security-Policy"] == "sandbox allow-scripts" and b"/~hyp/" not in body and body == (lib / "site/index.html").read_bytes()
    st, h, body = get(port, base + "site/index.html?hyp=dev")
    assert st == 200 and body.index(b"/~hyp/dev") < body.index(b"<title>")
    assert (lib / "site/index.html").read_text() == PAGE   # the file itself never changes
    st, h, body = get(port, base + "~hyp/dev")
    assert st == 200 and b"__hyDevAgent" in body and h["Content-Type"].startswith("text/javascript")
    st, h, body = get(port, base + "site/mod.js", {"Origin": "null"})
    assert st == 200 and h["Access-Control-Allow-Origin"] == "null"
    # path safety: nothing outside the library, no wrong key, no other site
    for bad in ("../secret.txt", "%2e%2e/secret.txt", "site/..%2f..%2fsecret.txt", "/etc/passwd", "%2Fetc%2Fpasswd", "~hyp/../manifest.json", "~hyp/nope"):
        assert get(port, base + bad)[0] == 404, bad
    assert get(port, "/sandbox/wrongkey/site/index.html")[0] == 404
    assert get(port, base + "site/index.html", {"Origin": "https://evil.example"})[0] == 403
    assert get(port, "/api/items", {"Origin": "null"})[0] == 403   # the null origin only on this route
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/file?p=site/x.html", data=b"x", method="POST", headers={"Origin": "null"})
    with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(req)
    assert e.value.code == 403 and not (lib / "site/x.html").exists()
    # its picture: the page drawn by Chromium (its css's blue), kept with the thumbnails, nothing written beside the page
    st, h, body = get(port, "/thumb?p=site/index.html&s=320")
    assert st == 200 and h["Content-Type"] == "image/jpeg"
    from PIL import Image
    im = Image.open(io.BytesIO(body)).convert("RGB"); r, g, b = im.getpixel((im.width // 2, im.height - 4))
    assert b > 150 and r < 60, (r, g, b)
    assert sorted(x.name for x in (lib / "site").iterdir()) == ["about.htm", "index.html", "mod.js", "style.css"]


def test_mode_switch_follows_selection_and_editors(hy):
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        assert list(modes(page)) == ["board", "image", "dev", "3d"]
        assert modes(page) == {"board": "on", "image": "off", "dev": "off", "3d": "off"}
        # the switch is icons alone (owner 2026-10-06: «look how Figma's switch is made, it's on the right and only the icon»); a disabled
        # segment's tooltip says what enables it
        titles = page.evaluate("Object.fromEntries([...document.querySelectorAll('#modes > button')].map(b => [b.dataset.mode, b.dataset.tip]))")
        assert page.evaluate("[...document.querySelectorAll('#modes > button')].map(b => b.textContent.trim()).join('')") == ""
        assert "Select an HTML card" in titles["dev"] and "Select a 3D card" in titles["3d"] and "Select one image or frame" in titles["image"]
        pick(page, ["i0"]); assert modes(page) == {"board": "on", "image": "can", "dev": "off", "3d": "off"}
        pick(page, ["h1"]); assert modes(page) == {"board": "on", "image": "off", "dev": "can", "3d": "off"}
        pick(page, ["m1"]); assert modes(page) == {"board": "on", "image": "off", "dev": "off", "3d": "can"}
        pick(page, ["i0", "i1"]); assert modes(page) == {"board": "on", "image": "off", "dev": "off", "3d": "off"}
        # a disabled segment does nothing
        page.click("#modes [data-mode=dev]", force=True); page.wait_for_timeout(200)
        assert not page.evaluate("!!__dev.D")
        # a double click enters Dev: the switch follows; Board leaves it
        page.dblclick(".plg[data-id=h1]")
        page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=15000)
        assert modes(page)["dev"] == "on" and modes(page)["board"] == "can"
        page.click("#modes [data-mode=board]")
        page.wait_for_function("() => !__dev.D && !document.querySelector('.dvui') && !document.querySelector('.plg[data-id=h1] iframe.dvf')")
        # the switch follows on the next frame (hyimg ui/modes.js sync() by requestAnimationFrame since d91e3c3): wait for it, not read it at once
        page.wait_for_function("() => document.querySelector('#modes [data-mode=board]').getAttribute('aria-pressed') === 'true'")
        # the segment enters it; Esc (two steps: the selected element, then Dev) leaves it
        pick(page, ["h1"]); page.click("#modes [data-mode=dev]")
        page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=15000)
        page.keyboard.press("Escape")
        page.wait_for_function("() => !__dev.D && document.querySelector('#modes [data-mode=board]').getAttribute('aria-pressed') === 'true'")
        # 3D: the segment opens the 3D studio for the selected card, Board closes it as its Done does
        pick(page, ["m1"]); page.click("#modes [data-mode=\"3d\"]")
        page.wait_for_function("() => document.body.classList.contains('m3edit')", timeout=30000)
        page.wait_for_function("() => document.querySelector('#modes [data-mode=\"3d\"]').getAttribute('aria-pressed') === 'true'")
        assert page.is_visible("#modes") and page.evaluate("document.getElementById('dock').classList.contains('plg-mode')")
        page.click("#modes [data-mode=board]")
        page.wait_for_function("() => !document.body.classList.contains('m3edit')", timeout=10000)
        page.wait_for_function("() => document.querySelector('#modes [data-mode=board]').getAttribute('aria-pressed') === 'true'")
        # Image: the picture becomes a frame of its own under its id, in place, with no step in the board's history until the first Save
        # (hyimg-frames a9ed877 and 2abd6b8, owner 2026-10-07: the studio on a picture leaves the board as it was unless saved; before, a new
        # frame with a new id replaced it as one undo step); the image studio opens for it; Board leaves it and the picture is back
        pick(page, ["i0"]); past = page.evaluate("past.length"); page.click("#modes [data-mode=image]")
        page.wait_for_function("() => window.__frames && __frames.ED && __frames.ED.win", timeout=30000)
        page.wait_for_function("() => document.querySelector('#modes [data-mode=image]').getAttribute('aria-pressed') === 'true'")
        assert page.evaluate("[board.items.i0.type, board.items.i0.pics, past.length]") == ["imgframe", ["a/0.png"], past]
        page.click("#modes [data-mode=board]")
        page.wait_for_function("() => !__frames.ED", timeout=10000)
        page.wait_for_function("() => !board.items.i0.type && board.items.i0.path === 'a/0.png'")
        page.wait_for_function("() => document.querySelector('#modes [data-mode=board]').getAttribute('aria-pressed') === 'true'")
        assert not errors, errors
        br.close()


@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_dev_mode_tree_page_and_inspector(hy, browser):
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port, browser)
        page.dblclick(".plg[data-id=h1]")
        page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        frame = next(f for f in page.frames if "/sandbox/" in f.url)
        # sandboxed: no allow-same-origin, the page cannot reach the board or storage, its module script ran (CORS with Origin null)
        assert page.get_attribute(".plg[data-id=h1] iframe.dvf", "sandbox") == "allow-scripts"
        frame.wait_for_function("() => document.body.dataset.mod === 'yes'", timeout=10000)
        assert frame.evaluate("document.body.dataset.parent") == "blocked" and frame.evaluate("document.body.dataset.storage") == "blocked"
        # the tree: html › head, body open; header, main inside; folded rows open with the chevron
        rows = page.locator(".dvt .row .dtg").all_inner_texts()
        assert rows[:3] == ["html", "head", "body"] and "header" in rows and "main" in rows
        page.click(".dvt .row:has(.dtg:text-is('main')) .chev"); page.click(".dvt .row:has(.dtg:text-is('section')) .chev")
        # hovering a row marks its element in the page
        page.hover(".dvt .row:has(.dia:text-is('#t'))")
        frame.wait_for_function("() => window.__hyDevAgent && document.querySelector('hy-dev-marks')")
        page.wait_for_timeout(200)
        # a click selects it: the inspector shows its tag, id, box and computed styles
        page.click(".dvt .row:has(.dia:text-is('#t'))")
        page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'h1'")
        d = page.evaluate("__dev.D.detail")
        want = frame.evaluate("(() => { const r = document.getElementById('t').getBoundingClientRect(); return [Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10] })()")
        assert [d["box"]["w"], d["box"]["h"]] == want and dict(d["styles"])["font-size"] == "48px" and ["id", "t"] in d["attrs"]
        txt = page.inner_text(".dvr")
        assert "h1" in txt and "48px" in txt and "#t" in txt
        # the select tool, off when Dev mode opens (owner 2026-10-08), I turns it on: a click in the page selects its element in the tree
        # (and never reaches the page)
        assert not page.evaluate("__dev.D.picking") and page.get_attribute(".dvbar [data-tool=pick]", "aria-pressed") == "false"
        page.evaluate("document.activeElement && document.activeElement.blur()"); page.keyboard.press("i")
        page.wait_for_function("() => __dev.D.picking"); assert page.get_attribute(".dvbar [data-tool=pick]", "aria-pressed") == "true"
        box = page.locator(".plg[data-id=h1] iframe.dvf").bounding_box()
        x, y = frame.evaluate("(() => { const r = document.getElementById('b').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2] })()")
        s = box["width"] / 1280
        page.mouse.move(box["x"] + x * s, box["y"] + y * s); page.wait_for_timeout(150)
        page.mouse.click(box["x"] + x * s, box["y"] + y * s)
        page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'button' && __dev.D.picking")
        assert page.inner_text(".dvt .row.sel").startswith("button") and frame.evaluate("document.querySelectorAll('li').length") == 2
        # the page is live: with the select tool off (I) a click reaches it, the tree follows the change
        page.click(".dvbar [data-tool=pick]"); page.wait_for_function("() => !__dev.D.picking")
        n0 = page.evaluate("__dev.D.tree.n")
        frame.click("#b"); frame.wait_for_function("() => document.querySelectorAll('li').length === 3")
        page.wait_for_function(f"() => __dev.D.tree.n === {n0} + 1", timeout=5000)
        # search: matching rows and the rows they sit in
        page.fill(".dvl input[data-q]", "Two"); page.wait_for_timeout(100)
        assert page.locator(".dvt .row .dtg").all_inner_texts() == ["html", "body", "main", "section", "ul", "li"]
        # ⌘. hides the panels with the board's interface (data-hyui, the board's zoom animation) and the marks in the page
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Meta+Period")
        page.wait_for_function("() => document.documentElement.classList.contains('hy-hideui')")
        assert page.evaluate("[...document.querySelectorAll('.dvl, .dvr')].every(e => e.hasAttribute('data-hyui') && getComputedStyle(e).animationName.startsWith('hyUi'))")
        frame.wait_for_function("() => document.querySelector('hy-dev-marks').style.display === 'none'")
        page.keyboard.press("Meta+Period")
        page.wait_for_function("() => !document.documentElement.classList.contains('hy-hideui')")
        # Done: everything of Dev mode goes, the card is a card again, the file never changed
        page.click("hy-studio-actions [data-a=done]")
        page.wait_for_function("() => !__dev.D && !document.querySelector('.dvui, .plg iframe.dvf')")
        assert (lib / "site/index.html").read_text() == PAGE
        assert not errors, errors
        br.close()


def test_drop_from_library_makes_a_page_card_with_a_live_preview(hy):
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.evaluate("""(() => { const dt = new DataTransfer(); dt.setData('text/x-frame', 'site/about.htm');
          const r = stage.getBoundingClientRect(); stage.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, clientX: r.left + 300, clientY: r.top + 700, bubbles: true, cancelable: true })); })()""")
        page.wait_for_function("() => Object.values(board.items).some(it => it.src === 'site/about.htm')")
        it = page.evaluate("Object.values(board.items).find(it => it.src === 'site/about.htm')")
        assert it["type"] == "html" and it["vw"] == 1280 and it["w"] == 320 and it["h"] == 200 and it["pics"] == ["site/about.htm"] and "path" not in it
        # big on screen the card runs its page (sandboxed, no pointer), small it shows the picture only
        page.evaluate("HY.camera(-40, 360, 1.6, false)")
        page.wait_for_function("() => document.querySelector('.plg[data-id=h1] iframe.dvpg')", timeout=10000)
        f = page.locator(".plg[data-id=h1] iframe.dvpg")
        assert f.get_attribute("sandbox") == "allow-scripts" and page.evaluate("getComputedStyle(document.querySelector('.plg[data-id=h1] iframe.dvpg')).pointerEvents") == "none"
        page.evaluate("HY.camera(-40, 360, 0.2, false)")
        page.wait_for_function("() => !document.querySelector('.plg iframe.dvpg')", timeout=10000)
        page.wait_for_function("() => document.querySelector('.plg[data-id=h1] img.dvi:not(.dvo)').src.endsWith('s=640')", timeout=10000)   # small again: the small still
        assert not errors, errors
        br.close()


@pytest.mark.parametrize("hy", ["ru"], indirect=True)
def test_russian_words(hy):
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        assert page.evaluate("[...document.querySelectorAll('#modes > button')].map(e => e.getAttribute('aria-label'))") == ["Доска", "Image Studio", "Dev Studio", "3D Studio"]   # the studios' names (owner 2026-10-08)
        page.dblclick(".plg[data-id=h1]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        assert page.get_attribute(".dvl input[data-q]", "placeholder") == "Найти элемент" and "Готово" in page.inner_text("hy-studio-actions")
        page.click(".dvt .row:has(.dtg:text-is('body'))"); page.wait_for_function("() => __dev.D.detail")
        assert "стили" in page.inner_text(".dvr").lower()
        assert page.evaluate("window.__tMiss.filter(k => k.startsWith('dev::'))") == []
        br.close()


def test_dock_stays_one_row(hy):
    port, lib, state = hy
    with sync_playwright() as p:
        for w in (1000, 1200, 1400, 1600):
            br, page, errors = board(p, port, size=(w, 900))
            r = page.evaluate("(() => { const d = document.getElementById('dock'); return { h: d.offsetHeight, over: d.scrollWidth - d.clientWidth, cls: document.getElementById('modes').className } })()")
            assert r["h"] <= 50 and r["over"] <= 1, (w, r)
            br.close()


def test_preview_cost(hy, capsys):
    """Measured, not asserted hard: frame times while panning 24 HTML cards, 4 of them live, against the same with live pages off."""
    port, lib, state = hy
    items = {f"h{k}": {"type": "html", "src": "site/index.html", "vw": 1280, "x": (k % 6) * 700, "y": (k // 6) * 460, "w": 640, "h": 400, "pics": ["site/index.html"]} for k in range(24)}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 2, "items": items, "groups": {}, "removed": {}}))
    out = {}
    with sync_playwright() as p:
        for live in (True, False):
            br, page, errors = board(p, port, size=(1600, 1000))
            page.evaluate("HY.camera(0, 0, 0.7, false)")
            if not live: page.evaluate("PLG.html.view = () => {}; document.querySelectorAll('iframe.dvpg').forEach(f => f.remove())")
            page.wait_for_timeout(2500)
            n = page.evaluate("document.querySelectorAll('iframe.dvpg').length")
            ms = page.evaluate("""async () => { const t = []; let last = performance.now();
              for (let k = 0; k < 120; k++) { await new Promise(r => requestAnimationFrame(r)); const now = performance.now(); t.push(now - last); last = now; HY.camera(HY.cam.x + 6, HY.cam.y, HY.cam.z, true); }
              t.sort((a, b) => a - b); return { med: t[60], p95: t[114], max: t[119] }; }""")
            out[live] = (n, ms)
            br.close()
    with capsys.disabled():
        print(f"\npan, 24 HTML cards at 70 %: live pages {out[True][0]} -> {out[True][1]}; none -> {out[False][1]}")
    assert out[True][0] <= 4
