"""Dev Studio's keys wait while someone types (owner 2026-10-10: «когда я в аннотациях пишу что-то, у меня триггерится F кнопка,
возможно и другие тоже, когда я тупо пишу сообщение»). Hyimg's one rule (its ui/typing.js): a field that takes text takes every key.
Dev mode's own keys (I the select tool, E Edit mode, C an annotation, P drawing, ⌫ an element) and the board's (F ♥, N a note, digits
the opacity) never fire while one of these is typed in, and the field holds the text as typed:

- the page's own fields in the live page: an input, and an input inside a web component's shadow root (the page's agent saw only the
  component, took I and E and ate the letters)
- the tree's search, an inspector field

Chromium, dark theme, a temporary library.  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_typing_keys.py"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import REPO, HERE, free_port

TEXT = "iecpfnlgtva IECPFN 0123456789 шуспатд zx"
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fields</title>
<style>body { margin: 0; font: 16px system-ui; background: #fff; } input { font: 16px system-ui; width: 600px; margin: 24px; display: block; }</style>
</head><body><h1 id="title">Fields</h1><input id="plain" placeholder="plain"><x-field id="shadowed"></x-field><p id="lead">Some text</p>
<script>
customElements.define('x-field', class extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: 'open' }).innerHTML = '<input placeholder="in a shadow root" style="font:16px system-ui;width:600px;margin:24px;display:block">'; }
});
</script></body></html>"""
STATE = """() => ({ picking: !!__dev.D.picking, edit: !!__dev.D.edit, commenting: !!__dev.D.commenting, items: Object.keys(board.items).sort(),
  op: Object.fromEntries(Object.entries(board.items).map(([k, v]) => [k, v.op ?? null])), faved: [...document.querySelectorAll('.faved')].length,
  tool: (window.hyAnnot && hyAnnot.active) || null, dev: !!__dev.D })"""


@pytest.fixture
def ed(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": "en", "cv.theme": "dark"}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/fields.html").write_text(PAGE)
    (plugins / "dev").symlink_to(HERE)
    items = {"e1": {"type": "html", "src": "site/fields.html", "vw": 1280, "x": 0, "y": 0, "w": 640, "h": 400, "pics": ["site/fields.html"]}}
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
        yield port, lib
    finally:
        proc.terminate(); proc.wait(5); log.close()


def same(page, before, what):
    after = page.evaluate(STATE)
    assert after == before, (what, before, after)


def test_dev_mode_keys_wait_while_its_fields_and_the_page_s_are_typed_in(ed):
    port, lib = ed
    with sync_playwright() as p:
        br = p.chromium.launch(); page = br.new_page(viewport={"width": 1500, "height": 950}, color_scheme="dark")
        errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        page.dblclick(".plg[data-id=e1]")
        page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.rev", timeout=20000)
        frame = next(fr for fr in page.frames if "/sandbox/" in fr.url)
        frame.wait_for_function("() => document.getElementById('shadowed').shadowRoot")
        last = None
        for _ in range(40):   # the camera's flight between the panels has ended
            page.wait_for_timeout(150); b = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
            if b == last: break
            last = b
        assert page.evaluate("__dev.D.picking") is False   # the page takes the clicks

        # the page's own input, and the one in a web component's shadow root
        for sel, read in (("#plain", "document.getElementById('plain').value"),
                          ("#shadowed input", "document.getElementById('shadowed').shadowRoot.querySelector('input').value")):
            frame.locator(sel).click(); before = page.evaluate(STATE)
            page.keyboard.type(TEXT); page.keyboard.press("Backspace")
            page.wait_for_timeout(200)   # a key the page's agent sent up would have arrived
            same(page, before, sel)
            assert frame.evaluate(f"() => {read}") == TEXT[:-1], sel
        frame.evaluate("() => document.activeElement.blur()")

        # the tree's search
        page.click(".dvl [data-q]"); before = page.evaluate(STATE)
        page.keyboard.type(TEXT)
        same(page, before, "the tree's search")
        assert page.evaluate("() => document.querySelector('.dvl [data-q]').value") == TEXT
        page.keyboard.press("Escape"); page.keyboard.press("Escape")

        # an inspector field of a selected element
        page.evaluate("() => { __dev.setPicking(true); }"); page.wait_for_function("() => __dev.D.picking")
        box = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
        x, y = frame.evaluate("(() => { const r = document.getElementById('lead').getBoundingClientRect(); return [r.left + 20, r.top + r.height / 2] })()")
        s = box["width"] / 1280; page.mouse.click(box["x"] + x * s, box["y"] + y * s)
        page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'p'", timeout=8000)
        f = page.locator(".dvr input[data-c='background-color']")
        f.click(); f.press("ControlOrMeta+a"); before = page.evaluate(STATE)
        page.keyboard.type(TEXT)
        same(page, before, "an inspector field")
        assert f.input_value() == TEXT
        f.press("Escape")
        assert not errors, errors
        br.close()
