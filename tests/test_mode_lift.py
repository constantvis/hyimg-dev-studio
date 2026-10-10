"""Entering a mode lifts the card it edits (owner 2026-10-08), on a board of 50 cards, Chromium, the dark theme, the setting «Тени» off:

- «Dev opens interactive»: the page takes the clicks (a press on its button reaches it), Select is off; I turns it on, and then a click
  picks the element instead (the page's button is not pressed again)
- in Dev, Image and 3D the board's selection around the card is gone while the mode is open (no outline, no corner squares) and a shadow
  stands under it once the enter animation ends; leaving sets it down and the selection comes back
- the cost: frame times while Dev mode opens (the camera's flight and the shadow growing in) against the same with the lift taken out

  HYIMG_REPO=<Hyimg checkout> nice -n 10 python3 -m pytest tests/test_mode_lift.py
  HYIMG_SHOTS=<folder> saves the screenshots, before and after each mode
"""
import io, json, os, subprocess, sys, time, urllib.request, uuid

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import REPO, HERE, REPOS, PAGE, CSS, free_port

SHOTS = os.environ.get("HYIMG_SHOTS")
COLS = [(200, 80, 80), (80, 160, 90), (70, 110, 200), (210, 170, 60), (150, 90, 190), (60, 170, 170), (230, 230, 225)]


def png(c, w=400, h=600):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (w, h), c).save(b, "PNG"); return b.getvalue()


@pytest.fixture
def lift(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": "en", "cv.shadow": "0"}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", lib / "a", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/index.html").write_text(PAGE); (lib / "site/style.css").write_text(CSS); (lib / "site/mod.js").write_text("export const v = 'yes';")
    for n, c in enumerate(COLS): (lib / "a" / f"{n}.png").write_bytes(png(c))
    (plugins / "dev").symlink_to(HERE)
    for n, repo in (("frames", "hyimg-image-studio"), ("3d", "hyimg-3d-studio")):
        if (REPOS / repo / "manifest.json").is_file(): (plugins / n).symlink_to(REPOS / repo)
    # 47 pictures in rows around the three cards a mode opens: an HTML page, a picture, a 3D scene
    items = {}
    for k in range(47):
        x, y = (k % 12) * 240 - 960, (k // 12) * 340 - 700
        if -300 < x < 1300 and -60 < y < 820: y += 1300   # the middle stays free for the three
        items[f"p{k}"] = {"path": f"a/{k % len(COLS)}.png", "x": x, "y": y, "w": 200, "ar": 2 / 3, "crop": None}
    items.update({"h1": {"type": "html", "src": "site/index.html", "vw": 1280, "x": 0, "y": 0, "w": 640, "h": 400, "pics": ["site/index.html"]},
                  "i0": {"path": "a/2.png", "x": 700, "y": 0, "w": 260, "ar": 2 / 3, "crop": None},
                  "m1": {"type": "model3d", "empty": True, "x": 0, "y": 460, "w": 400, "h": 300},
                  "f1": {"type": "htmlframe", "src": "site/index.html", "vw": 1280, "x": 480, "y": 460, "w": 480, "h": 300}})
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 1, "items": items, "groups": {}, "removed": {}}))
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HYIMG_", "REVIEW_"))}
    (tmp_path / "home").mkdir()
    env.update(HOME=str(tmp_path / "home"), PLAYWRIGHT_BROWSERS_PATH=os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(os.path.expanduser("~/Library/Caches/ms-playwright")))
    env.update(HYIMG_LIBRARY_ROOT=str(lib), HYIMG_STATE_ROOT=str(state), HYIMG_PROJECT_ID=str(uuid.uuid4()), HYIMG_PLUGINS=str(plugins),
               HYIMG_SETTINGS=str(tmp_path / "settings.json"), PYTHONDONTWRITEBYTECODE="1")
    log = open(tmp_path / "server.log", "w+")
    proc = subprocess.Popen([sys.executable, str(REPO / "review/server.py"), str(port)], env=env, stdout=log, stderr=log)
    for _ in range(100):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); break
        except OSError: time.sleep(0.1)
    try:
        yield port, lib, state
    finally:
        proc.terminate(); proc.wait(5); log.close()


def board(p, port, size=(1500, 950), args=()):
    br = p.chromium.launch(args=list(args))
    page = br.new_page(viewport={"width": size[0], "height": size[1]}, color_scheme="dark")
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    n = len(json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/plugins").read()))
    page.wait_for_function(f"() => typeof PLGST !== 'undefined' && PLGST.length === {n} && PLGST.every(x => x.ok)", timeout=30000)
    page.evaluate("HY.camera(-260, -160, 0.95, false)"); page.wait_for_timeout(600)
    return br, page, errors


def shot(page, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name))


def pick(page, ids):
    page.evaluate(f"(() => {{ sel = new Set({json.dumps(ids)}); render(); }})()"); page.wait_for_timeout(150)


# what the board shows around a card: its outline, the corner squares, the lift (its place against the card's and its layers' opacity)
STATE = """id => { const el = document.querySelector(`#items [data-id="${id}"]`), cs = el && getComputedStyle(el), L = document.getElementById('hylift');
  const r = el && el.getBoundingClientRect(), lr = L && L.getBoundingClientRect(), h = [...document.querySelectorAll('#handles > .h')];
  return { outline: cs ? (cs.outlineStyle === 'none' || parseFloat(cs.outlineWidth) === 0 ? 'none' : cs.outlineStyle) : 'gone',
    corners: h.length, cornersSeen: h.filter(x => getComputedStyle(x).opacity !== '0').length, mode: document.documentElement.dataset.hyEdit || '',
    boxSeen: [...document.querySelectorAll('#handles > .selbox')].filter(x => getComputedStyle(x).opacity !== '0' && getComputedStyle(document.getElementById('handles')).opacity !== '0').length,
    lift: !!L && L.classList.contains('on'), seen: !!L && getComputedStyle(L).visibility === 'visible',
    near: L ? +getComputedStyle(L.querySelector('.near')).opacity : 0, far: L ? +getComputedStyle(L.querySelector('.far')).opacity : 0,
    shadow: L ? getComputedStyle(L.querySelector('.far')).boxShadow : '', off: r && lr ? Math.max(Math.abs(r.left - lr.left), Math.abs(r.top - lr.top),
      Math.abs(r.width - lr.width), Math.abs(r.height - lr.height)) : -1, shadowSetting: document.documentElement.dataset.shadow }; }"""


# anything drawn round the card (owner 2026-10-08: «все равно обводка эта дурацкая вокруг появляется»): an outline, a border or a box-shadow
# on the card, on what it holds or on its ::before / ::after, a frame of the selection over it; the lift's shadow under it is not a ring
RINGS = """(id, card) => { const el = document.querySelector(`#items [data-id="${id}"]`), out = [];
  const drawn = (cs, who) => { if (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) out.push(who + ' outline ' + cs.outlineStyle);
    if (cs.boxShadow && cs.boxShadow !== 'none') out.push(who + ' box-shadow ' + cs.boxShadow.slice(0, 50));
    if (['Top', 'Right', 'Bottom', 'Left'].some(s => cs['border' + s + 'Style'] !== 'none' && parseFloat(cs['border' + s + 'Width']) > 0)) out.push(who + ' border'); };
  for (const e of [el, ...el.querySelectorAll('*')]) drawn(getComputedStyle(e), e.tagName.toLowerCase() + '.' + e.className);
  for (const p of ['::before', '::after']) { const cs = getComputedStyle(el, p); if (cs.content !== 'none' && cs.display !== 'none' && cs.opacity !== '0') drawn(cs, p); }
  const hs = !card && getComputedStyle(document.getElementById('handles')).opacity !== '0';   // card: the card alone (no mode, see below)
  for (const b of document.querySelectorAll('#handles > :is(.selbox, .mbox, .h)')) if (hs && getComputedStyle(b).opacity !== '0') out.push('handles ' + b.className);
  return out; }"""


def settled(page, id):
    page.wait_for_function("() => document.getElementById('hylift') && document.getElementById('hylift').classList.contains('on')", timeout=20000)
    page.wait_for_timeout(900)   # the camera's flight and the shadow's 420 ms
    return page.evaluate(STATE, id)


def test_dev_opens_interactive_and_i_turns_select_on(lift):
    port, lib, state = lift
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.dblclick(".plg[data-id=h1]")
        page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        frame = next(f for f in page.frames if "/sandbox/" in f.url)
        assert page.evaluate("__dev.D.picking") is False and page.get_attribute(".dvbar [data-tool=pick]", "aria-pressed") == "false"
        assert page.evaluate("[...document.querySelectorAll('.dvbar [data-tool]')].map(b => b.getAttribute('aria-pressed') + b.classList.contains('on')).join()") == "falsefalse,falsefalse"
        assert "The page takes the clicks" in page.inner_text(".dvr .dhint")
        # a press on the page's own button reaches the page: it adds a row to its list
        frame.wait_for_function("() => document.querySelectorAll('li').length === 2")
        frame.click("#b"); frame.wait_for_function("() => document.querySelectorAll('li').length === 3")
        # I (the page has the focus after that press) turns Select on; now a press picks the button and the page gets nothing
        page.keyboard.press("i"); page.wait_for_function("() => __dev.D.picking")
        assert page.get_attribute(".dvbar [data-tool=pick]", "aria-pressed") == "true"
        # the camera's flight into Dev mode may still be moving the card: measure once it stands (the same box 100 ms apart), or the
        # click lands beside the button
        page.wait_for_function("""() => { const r = document.querySelector('.plg[data-id=h1] iframe.dvf').getBoundingClientRect(), k = [r.x, r.y, r.width].join();
          const was = window.__box; window.__box = k; return was === k; }""", polling=100, timeout=10000)
        box = page.locator(".plg[data-id=h1] iframe.dvf").bounding_box()
        x, y = frame.evaluate("(() => { const r = document.getElementById('b').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2] })()")
        s = box["width"] / 1280
        page.mouse.move(box["x"] + x * s, box["y"] + y * s); page.wait_for_timeout(150); page.mouse.click(box["x"] + x * s, box["y"] + y * s)
        page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'button'")
        assert frame.evaluate("document.querySelectorAll('li').length") == 3
        # I again: the page takes the clicks once more; Dev mode opened again starts so, nothing is remembered for the card
        page.keyboard.press("Escape"); page.wait_for_function("() => !__dev.D.detail")
        page.keyboard.press("i"); page.wait_for_function("() => !__dev.D.picking")
        page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D")
        page.dblclick(".plg[data-id=h1]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        assert page.evaluate("__dev.D.picking") is False
        assert not errors, errors
        br.close()


def test_every_mode_lifts_its_card(lift):
    port, lib, state = lift
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        cases = [("dev", "h1", "() => __dev.D && __dev.D.tree", "() => !__dev.D"),
                 ("3d", "m1", "() => document.body.classList.contains('m3edit')", "() => !document.body.classList.contains('m3edit')"),
                 ("image", "i0", "() => window.__frames && __frames.ED && __frames.ED.win", "() => !__frames.ED")]
        for mode, id, opened, closed in cases:
            page.evaluate("""id => { const r = HY.rectOf(id), s = HY.stage.getBoundingClientRect(), z = 0.9;   // the card in the middle of the board
              HY.camera(r.x + r.w / 2 - s.width / 2 / z, r.y + r.h / 2 - s.height / 2 / z, z, false); }""", id)
            pick(page, [id]); page.wait_for_timeout(400)
            before = page.evaluate(STATE, id)
            assert (before["outline"] != "none" or before["boxSeen"]) and not before["lift"] and before["mode"] == "", (mode, before)   # a picture's frame is a .selbox
            shot(page, f"lift-{mode}-before-dark.png")
            page.click(f"#modes [data-mode=\"{mode}\"]")
            page.wait_for_function(opened, timeout=30000)
            s = settled(page, id)
            # the selection around it is gone (its corners unseen, still there for the 3D frame), a shadow under it, the setting «Тени» off
            assert s["outline"] == "none" and s["cornersSeen"] == 0 and s["boxSeen"] == 0 and s["mode"] == mode, (mode, s)
            assert s["lift"] and s["seen"] and s["near"] == 1 and s["far"] == 1 and "rgba(0, 0, 0" in s["shadow"], (mode, s)
            assert s["off"] <= 1.5 and s["shadowSetting"] == "0", (mode, s)
            if mode == "3d": assert s["corners"] == 4, "the frame's corners stay to grab, unseen"
            assert page.evaluate(RINGS, id) == [], mode
            # a click inside the card draws nothing round it either (selection, focus); in the image studio the click is the editor's
            b = page.evaluate("id => { const r = document.querySelector(`#items [data-id=\"${id}\"]`).getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", id)
            page.mouse.click(*b); page.wait_for_timeout(500)
            assert page.evaluate(RINGS, id) == [], (mode, "after a click inside")
            shot(page, f"lift-{mode}-after-dark.png")
            page.click("#modes [data-mode=board]")
            page.wait_for_function(closed, timeout=15000)
            page.wait_for_function("() => !document.documentElement.dataset.hyEdit && getComputedStyle(document.getElementById('hylift')).visibility === 'hidden'", timeout=5000)
            id = page.evaluate(f"board.items[{json.dumps(id)}] ? {json.dumps(id)} : Object.keys(board.items).find(k => board.items[k].type === 'imgframe') || {json.dumps(id)}")
            pick(page, [id])
            back = page.evaluate(STATE, id)
            assert (back["outline"] != "none" or back["boxSeen"]) and not back["lift"], (mode, back)
            shot(page, f"lift-{mode}-left-dark.png")
        assert not errors, errors
        br.close()


def wheel_at(page, box, dy, mods=()):
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2); page.wait_for_timeout(80)
    for m in mods: page.keyboard.down(m)
    page.mouse.wheel(0, dy); page.wait_for_timeout(350)
    for m in reversed(mods): page.keyboard.up(m)


def click_mid(page, sel):   # the middle of the page on screen: zoomed in, its corners go under the panels
    b = page.locator(sel).bounding_box(); page.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)


def pinch(page, sel, scale=1.6):
    """A real trackpad pinch (Chromium's synthetic one): the page under it gets ⌃ with the wheel first, and if nobody calls
    preventDefault, Chromium zooms the whole window, the board with its menus and panels (owner 2026-10-10, the video of Dev Studio).
    Only a pinch in shows it: the window never zooms out below 1. The board is taken back from its 8× cap first, so it can zoom in too;
    the pinch goes where the page itself is on top (not a panel over it), nearest the middle of the window."""
    page.evaluate("HY.camera(HY.cam.x, HY.cam.y, Math.min(HY.cam.z, 2), false)"); page.wait_for_timeout(300)
    pt = page.evaluate("""sel => { const f = document.querySelector(sel), W = innerWidth, H = innerHeight; let best = null;
      for (let y = 20; y < H; y += 20) for (let x = 20; x < W; x += 20) { if (document.elementFromPoint(x, y) !== f) continue;
        const d = Math.hypot(x - W / 2, y - H / 2); if (!best || d < best.d) best = { x, y, d }; }
      return best; }""", sel)
    assert pt, "the page is nowhere on top"
    s = page.context.new_cdp_session(page)
    s.send("Input.synthesizePinchGesture", {"x": pt["x"], "y": pt["y"], "scaleFactor": scale, "gestureSourceType": "mouse"})
    page.wait_for_timeout(400); s.detach()


def test_zoom_over_a_live_page(lift):
    """A pinch (⌃ with the wheel) over the live page zooms the board, not the page, and never the window, a click in the page or not
    (owner 2026-10-10: «приближается вообще вся наша картинка, и менюшки уходят за границы»; the state «The page has the zoom» a click
    gave is gone: «постоянно вот эта вот проблема возникает и препятствует»). ⌥ sends one gesture to the page, and to the board if the page
    does not take it; a plain wheel scrolls the page. Dev mode and the HTML frame."""
    port, lib, state = lift
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        z = lambda: page.evaluate("HY.cam.z")
        vv = lambda: page.evaluate("visualViewport.scale")
        own = lambda id: page.evaluate(f"document.querySelector('.plg[data-id={id}]').classList.contains('hy-page-own')")
        page.dblclick(".plg[data-id=h1]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        page.wait_for_timeout(2300)   # Dev mode fits the card again for 2 s after it opens (the library folding away)
        frame = next(f for f in page.frames if "/sandbox/" in f.url)
        # the page counts the pinches it sees and takes them (preventDefault) only while __take is on: most pages have no zoom of their own
        frame.evaluate("""(() => { const d = document.createElement('div'); d.style.height = '3000px'; document.body.appendChild(d);
          window.__n = 0; window.__take = false; addEventListener('wheel', e => { if (e.ctrlKey) { __n++; if (__take) e.preventDefault(); } }, { passive: false }); })()""")
        dvf = ".plg[data-id=h1] iframe.dvf"
        box = page.locator(dvf).bounding_box()
        # the board's: the camera zooms at the pointer, the page never sees the gesture and keeps its scale
        z0 = z(); wheel_at(page, box, -120, ["Control"])
        assert z() > z0 * 1.05 and frame.evaluate("__n") == 0 and frame.evaluate("visualViewport.scale") == 1
        # a plain wheel scrolls the page, the board stays
        box = page.locator(dvf).bounding_box(); z1 = z()
        wheel_at(page, box, 300); frame.wait_for_function("() => scrollY > 0")
        assert abs(z() - z1) < 1e-6
        # ⌥ with the pinch: that one to the page; a page that takes it keeps it, the board stays
        frame.evaluate("__take = true"); wheel_at(page, box, -120, ["Alt", "Control"])
        assert abs(z() - z1) < 1e-6 and frame.evaluate("__n") == 1
        # a page that does not take it: the board zooms, never the window
        frame.evaluate("__take = false"); wheel_at(page, box, -120, ["Alt", "Control"])
        assert frame.evaluate("__n") == 2 and z() > z1 * 1.05 and vv() == 1
        # a click in the page gives it nothing: no words in the dock, nothing round the card, the pinch is still the board's
        click_mid(page, dvf); page.wait_for_timeout(400)
        assert not own("h1") and not page.evaluate("!!document.querySelector('.dvbar .dvzh')") and page.evaluate(RINGS, "h1") == []
        shot(page, "lift-dev-click-in-page-dark.png")
        z2 = min(z(), 2); pinch(page, dvf)
        assert vv() == 1, "a pinch after a click in the page zoomed the whole window"
        assert z() > z2 * 1.05 and frame.evaluate("__n") == 2
        page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D"); page.wait_for_timeout(600)
        # the HTML frame's live view (the frames plugin, a page of the library's origin): the same rule from the host
        page.evaluate("HY.camera(300, 300, 1, false)"); page.wait_for_timeout(300)
        page.evaluate("PLG.htmlframe.dblclick('f1')"); page.wait_for_selector(".plg[data-id=f1] iframe.hfl")
        hf = page.frame_locator(".plg[data-id=f1] iframe.hfl"); hf.locator("h1").wait_for()
        hfl = ".plg[data-id=f1] iframe.hfl"
        box = page.locator(hfl).bounding_box()
        z3 = z(); wheel_at(page, box, -120, ["Control"]); assert z() > z3 * 1.05
        # the live view is no mode: the board's selection stays (its corners), but nothing of the live view's own is drawn round the card
        # (3D's global .plg-live outline drew there)
        assert page.evaluate(f"({RINGS})('f1', true)") == [], "the live view draws no frame round the card"
        click_mid(page, hfl); page.wait_for_timeout(400)
        assert not own("f1") and page.evaluate(f"({RINGS})('f1', true)") == []
        z4 = min(z(), 2); pinch(page, hfl)
        assert vv() == 1, "a pinch after a click in the HTML frame zoomed the whole window"
        assert z() > z4 * 1.05
        box = page.locator(hfl).bounding_box(); z5 = z(); wheel_at(page, box, -120, ["Alt", "Control"])
        assert z() > z5 * 1.05 and vv() == 1, "⌥ with a pinch the frame's page does not take goes to the board"
        assert not errors, errors
        br.close()


def test_enter_cost(lift, capsys):
    """Measured: frame times while Dev mode opens on 50 cards (the page loads, the camera flies, the shadow grows in), and while the camera
    zooms with the card lifted (its shadows keep their size on screen through --z), with the lift and without it (Chromium on Metal)."""
    port, lib, state = lift
    # one page, the lift shown and hidden by turns (on, off, off, on, ...), the frames of each kind pooled: a busy Mac weighs on both alike
    pool = {True: {"enter": [], "zoom": []}, False: {"enter": [], "zoom": []}}
    with sync_playwright() as p:
        br, page, errors = board(p, port, args=["--use-angle=metal"])
        page.add_style_tag(content="html.nolift #hylift { display: none !important; }"); page.wait_for_timeout(2500)
        cdp = page.context.new_cdp_session(page); cdp.send("Performance.enable")
        main = {True: {}, False: {}}   # the renderer's main thread during the zoom flights, ms: all tasks, style, layout
        for r in range(8):
            on = r % 4 in (0, 3)
            page.evaluate(f"document.documentElement.classList.toggle('nolift', {'false' if on else 'true'})")
            pick(page, ["h1"]); page.wait_for_timeout(400)
            pool[on]["enter"] += page.evaluate("""async () => { const t = []; let last = performance.now(), go = true;
              const tick = now => { t.push(now - last); last = now; if (go) requestAnimationFrame(tick); }; requestAnimationFrame(tick);
              document.querySelector('#modes [data-mode=dev]').click();
              await new Promise(r => setTimeout(r, 900)); go = false; return t.slice(1); }""")
            page.wait_for_timeout(2400)
            m0 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
            pool[on]["zoom"] += page.evaluate("""async () => { const t = [], c = { ...HY.cam }; let last = performance.now();
              for (let k = 0; k < 90; k++) { await new Promise(r => requestAnimationFrame(r)); const now = performance.now(); t.push(now - last); last = now;
                const z = c.z * Math.pow(1.006, k < 45 ? k : 90 - k); HY.camera(c.x, c.y, z, k < 89); }
              return t.slice(1); }""")
            m1 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
            for k in ("TaskDuration", "RecalcStyleDuration", "LayoutDuration"): main[on][k] = main[on].get(k, 0) + (m1[k] - m0[k]) * 1000
            page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D"); page.wait_for_timeout(900)
        assert not errors, errors
        br.close()
    def stats(t):
        s = sorted(t); q = lambda f: round(s[min(len(s) - 1, int(f * len(s)))], 1)
        return {"frames": len(s), "mean": round(sum(s) / len(s), 1), "med": q(.5), "p95": q(.95), "over20": sum(x > 20 for x in s)}
    out = {on: {k: stats(v) for k, v in d.items()} for on, d in pool.items()}
    with capsys.disabled():
        print(f"\n50 cards, Dev mode opened 4 times each (900 ms): with the lift {out[True]['enter']}, without {out[False]['enter']}"
              f"\n  zooming with the card lifted, 4 × 89 frames: {out[True]['zoom']}, without the lift {out[False]['zoom']}"
              f"\n  main thread over those flights, ms: with {({k: round(v) for k, v in main[True].items()})}, without {({k: round(v) for k, v in main[False].items()})}")
    assert out[True]["zoom"]["frames"] == out[False]["zoom"]["frames"] == 4 * 89
