"""A colour on a row of Dev mode's element tree (owner 2026-10-07: «в layers при нажатии правой кнопки добавить colors как в notes ... и так
в любых: 3D editor, image editor»).

A right click on a row opens the board's menu with the notes' swatch row first, «no colour» its first swatch; a swatch marks the row with
the app's stripe (Hyimg ui/menu.js .hy-rc) and lands in the card's item on the board, treeColors, keyed by the row's place in the page
(«html>body:1>main:1»), never in the page's file. It survives Done, a reload of the board and opening Dev mode again; the board's ⌘Z takes
a colour back; «no colour» clears it. Chromium and WebKit.

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_tree_colors.py
  HYIMG_SHOTS=<folder> also saves screenshots
"""
import json, os, time

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import PAGE, board, hy   # noqa: F401 (hy is the fixture)

SHOTS = os.environ.get("HYIMG_SHOTS")
ROW = lambda tag: f".dvt .row:has(> .nm > .dtg:text-is('{tag}'))"
MAIN, HEADER = "html>body:1>main:1", "html>body:1>header:0"


def saved(state, cond, t=8):
    """the board's file once cond holds for the page card's treeColors"""
    end = time.time() + t
    while True:
        try: c = json.loads((state / "boards/main.json").read_text())["items"]["h1"].get("treeColors") or {}
        except (OSError, ValueError, KeyError): c = None
        if c is not None and cond(c): return c
        if time.time() > end: raise AssertionError(f"treeColors on the board: {c}")
        time.sleep(0.1)


def open_dev(page):
    page.dblclick(".plg[data-id=h1]")
    page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
    page.wait_for_selector(ROW("main"))


def menu(page, tag, color):
    page.click(ROW(tag), button="right"); page.wait_for_selector("#ctx.open .msw button[data-color=blue]")
    first = page.evaluate("() => { const f = document.querySelector('#ctx.open').firstElementChild; return { msw: f.classList.contains('msw'), c: f.querySelector('button').dataset.color }; }")
    assert first == {"msw": True, "c": ""}, first
    page.click(f"#ctx.open .msw button[data-color='{color}']"); page.wait_for_timeout(200)
    assert not page.evaluate("() => document.getElementById('ctx').classList.contains('open')")


def stripe(page, tag):
    return page.locator(ROW(tag)).evaluate("""r => ({ on: r.classList.contains('hy-rc'), c: r.style.getPropertyValue('--hy-rc'),
      bg: getComputedStyle(r, '::before').backgroundColor, w: getComputedStyle(r, '::before').width })""")


@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_a_tree_row_takes_a_colour_kept_on_the_card(hy, browser):
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port, browser)
        open_dev(page)
        assert page.locator(ROW("main")).get_attribute("data-p") == MAIN
        # a right click: the swatch row first; blue marks the row with the stripe and lands on the card
        menu(page, "main", "blue")
        s = stripe(page, "main")
        assert s == {"on": True, "c": "#7dbbf5", "bg": "rgb(125, 187, 245)", "w": "3px"}, s
        assert not stripe(page, "header")["on"], "only that row"
        saved(state, lambda c: c == {MAIN: "blue"})
        # the board's ⌘Z takes a colour back
        menu(page, "header", "red"); saved(state, lambda c: c.get(HEADER) == "red")
        page.evaluate("document.activeElement && document.activeElement.blur()"); page.keyboard.press("Meta+z")
        saved(state, lambda c: c == {MAIN: "blue"})
        page.wait_for_function("() => !document.querySelector('.dvt .row.hy-rc[data-p=\"html>body:1>header:0\"]')")
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            for th in ("dark", "light"):
                page.evaluate(f"() => document.documentElement.dataset.theme = '{th}'"); page.wait_for_timeout(300)
                page.screenshot(path=os.path.join(SHOTS, f"colors-dev-{th}-{browser}.png"))
            page.evaluate("() => delete document.documentElement.dataset.theme")
        # the colour survives Done, a reload of the board and Dev mode again; the page's file never changes
        page.click(".dvbar [data-a=done]"); page.wait_for_function("() => !__dev.D")
        page.wait_for_timeout(800); page.reload()
        page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
        open_dev(page)
        assert stripe(page, "main")["c"] == "#7dbbf5"
        # «no colour» clears it, and the card loses the field
        menu(page, "main", "")
        assert not stripe(page, "main")["on"]
        saved(state, lambda c: c == {})
        assert "treeColors" not in json.loads((state / "boards/main.json").read_text())["items"]["h1"]
        assert (lib / "site/index.html").read_text() == PAGE
        assert not errors, errors
        br.close()
