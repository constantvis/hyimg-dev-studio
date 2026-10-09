"""Comments and drawings on HTML (owner 2026-10-07: «чтобы я мог добавлять либо поверх картинки статичной, либо еще как»). On a disposable
library, Chromium, the dark theme, English and Russian:

- on the board, Annotate draws over an HTML card whose page runs live in it and over the frames plugin's HTML frame in its live view: the
  tools take the pointer from the page (its iframe lets it through only while a tool is on), a stroke and a pin anchor to the card and
  move with it, the live view and its dock come back on Done, and the page takes clicks again
- in Dev mode the Comment tool (C) pins a thread to an element of the page: its key in the tree, a css selector, its text, the point in the
  page; the pin stands on the element in the live page and on the card's still after Done; Draw (P) draws over the page, anchored to the
  card; hy.py comments names the element

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_comments.py      HYIMG_SHOTS=<folder> saves the screenshots
"""
import json, os, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import REPO, REPOS, HERE, PAGE, CSS, free_port

SHOTS = os.environ.get("HYIMG_SHOTS")
ME = str(uuid.uuid4())
FRAME = "<!doctype html><html><body style='margin:0;background:#2a6;font:40px system-ui'><button id=go style='margin:80px'>Go</button>" \
        "<script>document.getElementById('go').onclick = () => document.body.dataset.clicked = '1'</script></body></html>"


@pytest.fixture(params=["en", "ru"])
def hy(tmp_path, request):
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": request.param, "cv.theme": "dark"}))
    (tmp_path / "profile.json").write_text(json.dumps({"id": ME, "name": "Ann Lee", "color": "green", "created": ""}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", lib / "html/f", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/index.html").write_text(PAGE); (lib / "site/style.css").write_text(CSS); (lib / "site/mod.js").write_text("export const v = 'yes';")
    (lib / "html/f/index.html").write_text(FRAME)
    (plugins / "dev").symlink_to(HERE)
    frames = (REPOS / "hyimg-image-studio" / "manifest.json").is_file()
    if frames: (plugins / "frames").symlink_to(REPOS / "hyimg-image-studio")
    items = {"h1": {"type": "html", "src": "site/index.html", "vw": 1280, "x": 0, "y": 0, "w": 640, "h": 400, "pics": ["site/index.html"]}}
    if frames: items["f1"] = {"type": "htmlframe", "src": "html/f/index.html", "vw": 1280, "x": 700, "y": 0, "w": 640, "h": 400}
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
        yield port, lib, request.param, frames
    finally:
        proc.terminate(); proc.wait(5); log.close()


def get(port, path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10))


def wait(fn, what, t=10):
    end = time.time() + t
    while time.time() < end:
        v = fn()
        if v: return v
        time.sleep(0.1)
    raise AssertionError(what)


def shot(page, name):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name))


def board(p, port, draw=True):
    """draw: Hyimg's drawing tools, put off on 2026-10-09 behind the flag cv.annDraw (hyimg docs/LATER.md); these tests keep them working"""
    br = p.chromium.launch()
    page = br.new_page(viewport={"width": 1600, "height": 960}, color_scheme="dark")
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    page.evaluate("() => { localStorage.setItem('cv.nolib', '1'); localStorage.setItem('cv.lod', '0'); }" if not draw else
                  "() => { localStorage.setItem('cv.nolib', '1'); localStorage.setItem('cv.lod', '0'); localStorage.setItem('cv.annDraw', '1'); }")
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok) && window.hyAnnot && document.getElementById('bann')"
                           " && window.hyPeople && hyPeople.me()" + (" && hyAnnot.drawing" if draw else ""), timeout=30000)
    page.evaluate("() => { cam.x = -40; cam.y = -120; cam.z = 1; saveCam(); renderCam(); render(); }")
    return br, page, errors


def box(page, sel):
    return page.locator(sel).bounding_box()


def stroke(page, b, fx=.3, fy=.4):
    page.mouse.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy); page.mouse.down()
    for i in range(12): page.mouse.move(b["x"] + b["width"] * fx + i * 14, b["y"] + b["height"] * fy + (i % 3) * 12)
    page.mouse.up()


def test_annotate_over_live_html_cards_on_the_board(hy):
    port, lib, lang, frames = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        # the HTML card runs its page live at this size (Dev studio's preview)
        page.wait_for_selector(".plg[data-id=h1].pv iframe.dvpg", timeout=20000)
        page.keyboard.press("p")
        assert page.locator(".plg[data-id=h1] iframe.dvpg").evaluate("f => getComputedStyle(f).pointerEvents") == "none"
        stroke(page, box(page, ".plg[data-id=h1]"))
        a = wait(lambda: get(port, "/api/annotations?name=main")["items"], "no stroke on the HTML card")[0]
        assert a["anchor"]["obj"] == "h1" and a["anchor"]["kind"] == "html" and a["anchor"]["file"] == "site/index.html"
        g0 = box(page, f'#annsvg g[data-a="{a["id"]}"]')
        page.evaluate("() => { board.items.h1.y += 60; render(); }")
        g1 = box(page, f'#annsvg g[data-a="{a["id"]}"]')
        assert abs(g1["y"] - g0["y"] - 60) < 1.5
        page.evaluate("() => { board.items.h1.y -= 60; render(); }")
        page.keyboard.press("Escape")
        if frames:
            # the HTML frame's live view: the page takes clicks, its own dock
            page.evaluate("() => PLG.htmlframe.dblclick('f1')")
            page.wait_for_selector(".plg[data-id=f1].plg-live iframe.hfl")
            page.wait_for_selector("#dock .hfbar")
            fr = page.frame_locator(".plg[data-id=f1] iframe.hfl")
            fr.locator("#go").click()
            assert fr.locator("body").get_attribute("data-clicked") == "1"
            # Annotate over it: the tools borrow the dock, the page lets the pointer through, the live view stays
            page.evaluate("() => { document.activeElement.blur(); window.focus(); }")   # the keys to the board, as a click on the dock gives them
            page.keyboard.press("p"); page.keyboard.press("r")
            page.wait_for_selector("#dock .ann-bar [data-tool=rect].on")
            assert page.locator(".plg[data-id=f1] iframe.hfl").evaluate("f => getComputedStyle(f).pointerEvents") == "none"
            b = box(page, ".plg[data-id=f1]")
            page.mouse.move(b["x"] + 100, b["y"] + 100); page.mouse.down(); page.mouse.move(b["x"] + 300, b["y"] + 220, steps=6); page.mouse.up()
            r = wait(lambda: [x for x in get(port, "/api/annotations?name=main")["items"] if x["kind"] == "rect"], "no rectangle on the live frame")[0]
            assert r["anchor"]["obj"] == "f1" and page.locator(".plg[data-id=f1].plg-live").count() == 1
            page.keyboard.press("c"); page.mouse.click(b["x"] + 400, b["y"] + 120)
            page.wait_for_selector("#cmthread.open textarea"); page.keyboard.type("This button is too small"); page.keyboard.press("Enter")
            t = wait(lambda: get(port, "/api/comments?name=main")["items"], "no comment on the live frame")[0]
            assert t["anchor"]["obj"] == "f1"
            page.wait_for_selector(f'#cmpins [data-c="{t["id"]}"]')
            shot(page, f"html-{lang}-1-live-frame.png")
            page.keyboard.press("Escape"); page.keyboard.press("Escape")   # the thread, then the tools
            page.wait_for_selector("#dock .hfbar")
            assert page.locator("#dock .ann-bar").count() == 0 and page.locator(".plg[data-id=f1].plg-live").count() == 1
            assert page.locator(".plg[data-id=f1] iframe.hfl").evaluate("f => getComputedStyle(f).pointerEvents") == "auto"
            # the pin and the rectangle move with the frame
            p0 = box(page, f'#cmpins [data-c="{t["id"]}"]'); page.evaluate("() => { board.items.f1.x += 40; render(); }")
            assert abs(box(page, f'#cmpins [data-c="{t["id"]}"]')["x"] - p0["x"] - 40) < 1.5
        assert not errors, errors
        br.close()


def test_dev_mode_comments_on_elements_and_draws_over_the_page(hy):
    port, lib, lang, frames = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.evaluate("() => __dev.openDev('h1')")
        page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.tree.root", timeout=20000)
        page.wait_for_timeout(700)   # the camera's flight
        page.locator("#dock .dvbar [data-tool=comment]").click()
        assert page.locator("#dock .dvbar [data-tool=comment]").get_attribute("aria-pressed") == "true"
        f = page.frame_locator(".plg[data-id=h1] iframe.dvf")
        fb = box(page, ".plg[data-id=h1] iframe.dvf"); s = fb["width"] / 1280
        r = f.locator("#t").evaluate("el => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        page.mouse.click(fb["x"] + (r[0] + 20) * s, fb["y"] + (r[1] + r[3] / 2) * s)
        page.wait_for_selector("#cmthread.open textarea")
        page.keyboard.type("Make the heading bigger"); page.keyboard.press("Enter")
        t = wait(lambda: get(port, "/api/comments?name=main")["items"], "no comment on the element")[0]
        assert t["anchor"]["obj"] == "h1" and t["element"]["css"] == "#t" and t["element"]["tag"] == "h1" and t["element"]["text"] == "Hello"
        assert t["element"]["key"] == "html>body:1>main:1>section:0>h1:0", t["element"]
        assert 0 < t["at"][0] < .5 and 0 < t["at"][1] < .5
        # the pin stands on the element in the live page
        pin = box(page, f'#cmpins [data-c="{t["id"]}"]')
        ex, ey = fb["x"] + r[0] * s, fb["y"] + r[1] * s
        assert ex - 4 <= pin["x"] <= ex + r[2] * s and ey - pin["height"] - 4 <= pin["y"] <= ey + r[3] * s, (pin, ex, ey)
        shot(page, f"dev-{lang}-1-element-comment.png")
        page.keyboard.press("Escape")   # the thread
        # Draw over the page: the board's tools borrow Dev mode's dock and give it back
        page.locator("#dock .dvbar [data-a=draw]").click()
        page.wait_for_selector("#dock .ann-bar [data-tool=pen].on")
        stroke(page, box(page, ".plg[data-id=h1]"), .5, .6)
        a = wait(lambda: get(port, "/api/annotations?name=main")["items"], "no stroke over the page")[0]
        assert a["anchor"]["obj"] == "h1"
        shot(page, f"dev-{lang}-2-draw.png")
        page.keyboard.press("Escape")
        page.wait_for_selector("#dock .dvbar [data-tool=comment]")
        assert page.locator("#dock .ann-bar").count() == 0 and page.evaluate("() => !!__dev.D")
        # an agent reads it: the element named
        env = {k: v for k, v in os.environ.items() if not k.startswith("HYIMG_")} | {"HYIMG_PORT": str(port), "PYTHONDONTWRITEBYTECODE": "1"}
        out = subprocess.run([sys.executable, str(REPO / "review/hy.py"), "comments", "--page", "main"], env=env, capture_output=True, text=True, timeout=60)
        assert out.returncode == 0 and "#t" in out.stdout and "Make the heading bigger" in out.stdout, out.stdout + out.stderr
        # Done: the pin on the card's still, at the element's place
        page.keyboard.press("Escape"); page.keyboard.press("Escape")
        page.wait_for_function("() => !__dev.D"); page.wait_for_timeout(600)
        cb, pin = box(page, ".plg[data-id=h1]"), box(page, f'#cmpins [data-c="{t["id"]}"]')
        assert abs(pin["x"] - (cb["x"] + t["at"][0] * cb["width"])) < 2 and abs(pin["y"] + pin["height"] - (cb["y"] + t["at"][1] * cb["height"])) < 3
        shot(page, f"dev-{lang}-3-board-pin.png")
        assert not errors, errors
        br.close()
