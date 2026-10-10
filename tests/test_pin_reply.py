"""A click on an annotation's pin in Dev Studio puts the cursor in the reply at once, as on the board (owner 2026-10-10, round 18
question 20, r18-small.html, version A: «Да, все окей, давай так»). The thread is the board's (Hyimg ui/comments.js hyComments.open, one
rule for the board and every Studio): after the click the letters typed are the reply, the Studio's keys stay quiet (E would switch
Edit mode). The same for the count on an element's row in the tree. Chromium, dark, the mouse.

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_pin_reply.py
"""
from playwright.sync_api import sync_playwright

from test_tree_comments import ROW, hy, write  # noqa: F401  (hy is the fixture)

FOCUS = "() => !!(document.activeElement && document.activeElement.matches('#cmthread.open textarea'))"


def test_a_click_on_a_pin_in_dev_studio_puts_the_cursor_in_the_reply(hy):
    port = hy
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={"width": 1600, "height": 960}, color_scheme="dark")
        errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.evaluate("() => { localStorage.setItem('cv.nolib', '1'); localStorage.setItem('cv.lod', '0'); }")
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok) && window.hyAnnot && window.hyComments"
                               " && window.hyPeople && hyPeople.me()", timeout=30000)
        page.evaluate("() => __dev.openDev('h1')")
        page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.tree.root", timeout=20000)
        page.wait_for_selector('.dvt .row[data-p="html>body:1>header:0"]')
        page.locator('.dvt .row[data-p="html>body:1>header:0"] .chev').click(); page.wait_for_selector(ROW("t"))
        page.hover(ROW("t")); page.click(f"{ROW('t')} .dvcb")
        tid = write(page, port, "Bigger heading")["id"]
        page.keyboard.press("Escape"); page.wait_for_function("() => !document.querySelector('#cmthread.open')")
        page.mouse.move(5, 500); page.wait_for_selector(f'#cmpins [data-c="{tid}"]')
        assert not page.evaluate("() => __dev.D.edit")

        # the pin on the live page: a click, the reply has the cursor, E goes into it and not to Edit mode
        page.locator(f'#cmpins [data-c="{tid}"]').click()
        page.wait_for_selector(f'#cmthread.open[data-c="{tid}"] textarea')
        page.wait_for_function(FOCUS, timeout=3000)
        page.keyboard.type("yes")
        assert page.evaluate("() => document.querySelector('#cmthread textarea').value") == "yes"
        assert not page.evaluate("() => __dev.D.edit")
        page.keyboard.press("Escape"); page.wait_for_function("() => !document.querySelector('#cmthread.open')")

        # the count on the element's row: the same
        page.locator(f"{ROW('t')} .dvcn").click()
        page.wait_for_selector(f'#cmthread.open[data-c="{tid}"] textarea')
        page.wait_for_function(FOCUS, timeout=3000)
        page.keyboard.type(" e")
        assert page.evaluate("() => document.querySelector('#cmthread textarea').value") == "yes e"
        assert not page.evaluate("() => __dev.D.edit")
        assert not errors, errors
        br.close()
