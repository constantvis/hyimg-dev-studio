"""HTML cards fade like pictures (owner 2026-10-06: a card on the board is a picture for its look): the Dev studio's page card and the
frames plugin's HTML frame take the bar's opacity slider and the keys 1…9, 0, one step to undo, carried by «Copy/Paste properties».
Their colour grade stays off: the live page in them is not a picture a grade could go over.

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_card_opacity.py
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import board, hy, pick   # noqa: F401 (hy is the fixture)

WEBKIT = any(Path(os.path.expanduser("~/Library/Caches/ms-playwright")).glob("webkit-*"))
OP = "id => getComputedStyle(document.querySelector(`.plg[data-id='${id}']`)).opacity"


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_html_cards_take_the_opacity(hy, engine):
    if engine == "webkit" and not WEBKIT: pytest.skip("no Playwright WebKit")
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port, engine)
        if not page.evaluate("() => PLGST.some(x => x.name === 'frames' && x.ok)"): pytest.skip("no frames plugin beside this one")
        page.evaluate("() => { board.items.f1 = { type: 'htmlframe', src: 'site/index.html', vw: 1280, x: 1200, y: 0, w: 400, h: 250 }; render(); }")
        page.wait_for_selector(".plg[data-id=f1]")
        for id in ("h1", "f1"):
            pick(page, [id])
            assert page.locator(".tidy [data-op]").count() == 1, page.evaluate("() => document.querySelector('#handles').innerHTML")
            page.evaluate("() => { const i = document.querySelector('.tidy [data-op]'); i.value = 40; i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); }")
            page.wait_for_function(f"() => board.items.{id}.opacity === 0.4")
            assert page.evaluate(OP, id) == "0.4"
            page.keyboard.press("Meta+z")
            page.wait_for_function(f"id => board.items[id].opacity === undefined && getComputedStyle(document.querySelector(`.plg[data-id='${{id}}']`)).opacity === '1'", arg=id)
            page.keyboard.press("Digit6")
            page.wait_for_function(f"() => board.items.{id}.opacity === 0.6")
            # the grade does not apply to a live page: no Raw Editor button, grey in «Copy properties»
            assert page.locator('.tidy button[aria-label="Raw Editor"]').count() == 0
            assert page.evaluate(f"() => appliesTo(PROPS.get('grade'), board.items.{id})") is not True
        # Copy/Paste properties: a page card's opacity onto a picture and a picture's onto the HTML frame
        page.evaluate("() => { copyProps('h1', ['opacity']); const c = propsClip(); return pasteProps(c.kinds, ['i0'], c.src, null, c); }")
        page.wait_for_function("() => board.items.i0.opacity === 0.6")
        page.evaluate("() => { board.items.i1.opacity = 0.3; copyProps('i1', ['opacity']); const c = propsClip(); return pasteProps(c.kinds, ['f1'], c.src, null, c); }")
        page.wait_for_function("() => board.items.f1.opacity === 0.3")
        assert page.evaluate(OP, "f1") == "0.3"
        assert not errors, errors
        br.close()
