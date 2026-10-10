"""Dev Studio's medium and low findings of the П4 logic audit (2026-10-10, hyimg docs/process.md §5) and the owner's decisions of that day,
each as the person meets it. Chromium, the dark theme, a temporary library; each fails on the code before:

- S-30 V turns Select on and off, as in Image Studio and 3D Studio
- S-37 ↵ on a focused button presses the button (Hyimg's hyTyping.ownKey since S-15), no typing starts in the page
- S-35 Esc in the page's own field stays with the page: Dev Studio keeps its selection and stays open
- S-59 a number's Esc puts it back whenever it comes: ↑ ↑ and a second later Esc, nothing is written; History names it «Corners»
- S-39 a write the server refuses says why in words (no bare status), and the file's LED turns red
- S-40 an edit that went in beside a change made outside says so and offers Reload
- S-51 ⌫ leaves nothing chosen, its ⌘Z chooses the element again
- S-59 after Reload the change dot stays on the changed element's row; ⇧↵ typing in the page writes no line break
- S-41 Reload of a page whose file is gone says so, it does not load forever
- S-50 ⌥R reloads the page in Dev Studio, not the board (owner 2026-10-10: ⌥R, not ⌘R; ⌘R is never ours, a browser reloads its tab)
- S-28 ⌘↵ is Done

  HYIMG_REPO=<Hyimg checkout> nice -n 10 python3 -m pytest tests/test_p4_medium.py
"""
import time

from playwright.sync_api import sync_playwright

from test_dev_edit import ed, click_in, picked, PAGE  # noqa: F401  (ed is the fixture)
from test_p4_logic import open_board, open_dev, blur, toasts


def test_select_key_page_field_number_and_errors(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"
    f.write_text(PAGE.replace('<div id="made"></div>', '<div id="made"></div><input id="q" value="find">'))
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        frame = open_dev(page)
        # S-30: V is Select
        blur(page); was = page.evaluate("__dev.D.picking"); page.keyboard.press("v"); page.wait_for_timeout(200)
        assert page.evaluate("__dev.D.picking") != was, "V did not switch Select"
        page.keyboard.press("v"); page.wait_for_timeout(200)
        # S-37: ↵ on a focused button presses it, it types no text in the page
        click_in(page, frame, "#title"); picked(page, "h1")
        page.focus(".dvr [data-tab=hist]"); page.keyboard.press("Enter"); page.wait_for_timeout(300)
        assert page.evaluate("() => __dev.D.tab") == "hist" and not page.evaluate("() => !!__dev.D.typed"), "↵ on a button typed in the page"
        page.click(".dvr [data-tab=insp]")
        # S-35: the page's own field keeps Esc
        click_in(page, frame, "#title"); picked(page, "h1")
        if page.evaluate("__dev.D.picking"): blur(page); page.keyboard.press("v"); page.wait_for_function("() => !__dev.D.picking")
        frame.click("#q"); frame.wait_for_timeout(200); frame.press("#q", "Escape"); page.wait_for_timeout(500)
        assert page.evaluate("() => !!__dev.D && __dev.D.sels.size === 1"), "Esc in the page's field stepped Dev Studio out"
        blur(page); page.keyboard.press("v"); page.wait_for_function("() => __dev.D.picking")
        # S-59: ↑ ↑, a second later Esc: the number back, nothing written
        click_in(page, frame, "#title"); picked(page, "h1")
        raw = f.read_bytes(); n = page.locator(".dvr input[data-n=border-radius]"); n.click()
        page.keyboard.press("ArrowUp"); page.keyboard.press("ArrowUp"); page.wait_for_timeout(1200); page.keyboard.press("Escape"); page.wait_for_timeout(800)
        assert f.read_bytes() == raw, "Esc a second after ↑ ↑ still wrote the number"
        # History in the inspector's words
        n.click(); page.keyboard.press("ArrowUp"); page.keyboard.press("Enter")
        page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000)
        page.click(".dvr [data-tab=hist]"); assert "Corners" in page.inner_text(".dvr .dvhl"); page.click(".dvr [data-tab=insp]")
        # S-39: a refused write in words, the LED red
        page.route("**/api/plugin/dev/edit", lambda r: r.fulfill(status=500, body=""))
        toasts(page); click_in(page, frame, "#title"); picked(page, "h1")
        n = page.locator(".dvr input[data-n=border-radius]"); n.click(); page.keyboard.press("ArrowUp"); page.keyboard.press("Enter"); page.wait_for_timeout(1500)
        said = [t for t, k in toasts(page) if k == "error"]
        assert said and not any("500" in t for t in said), said
        assert len(said) == 1, said
        assert page.get_attribute(".dvr .ih .dvled", "state") == "err"
        page.unroute("**/api/plugin/dev/edit")
        # S-40: a change made outside, then an edit: it goes in, a note says so with Reload
        f.write_text(f.read_text().replace("</body>", "<!-- outside --></body>")); toasts(page)
        click_in(page, frame, "#title"); picked(page, "h1")
        n = page.locator(".dvr input[data-n=border-radius]"); n.click(); page.keyboard.press("ArrowUp"); page.keyboard.press("Enter"); page.wait_for_timeout(2000)
        assert any("outside" in t for t, k in toasts(page)), "an edit beside a change made outside said nothing"
        assert "<!-- outside -->" in f.read_text()
        assert not errors, errors
        br.close()


def test_delete_reload_and_leaving(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        page.evaluate("() => { window.__board = 1; }")
        frame = open_dev(page)
        page.evaluate("__dev.setEdit(true)"); page.wait_for_timeout(300)
        # S-51: ⌫ leaves nothing chosen; ⌘Z chooses it again
        click_in(page, frame, "#lead"); picked(page, "p")
        blur(page); page.keyboard.press("Backspace"); page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000)
        assert page.evaluate("() => __dev.D.sels.size") == 0, "a removed element stayed chosen"
        blur(page); page.keyboard.press("Meta+z"); page.wait_for_function("() => __dev.D.past.length === 0", timeout=8000); page.wait_for_timeout(500)
        assert page.evaluate("() => __dev.D.detail && __dev.D.detail.t") == "p", "⌘Z did not choose the element again"
        # S-59: ⇧↵ typing in the page writes no line break; the change dot stays on its row after Reload
        click_in(page, frame, "#title"); picked(page, "h1")
        click_in(page, frame, "#title", dbl=True); page.wait_for_timeout(400)
        page.keyboard.press("End"); page.keyboard.press("Shift+Enter"); page.keyboard.type("X"); page.keyboard.press("Enter")
        page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000); page.wait_for_timeout(500)
        assert "Hello worldX" in f.read_text() and "<br" not in f.read_text()
        page.click(".dvui hy-studio-actions [data-a=reload]"); page.wait_for_function("() => __dev.D.tree", timeout=10000); page.wait_for_timeout(800)
        page.evaluate("() => { const w = n => n.t === 'header' ? n : (n.k || []).map(w).find(Boolean); __dev.D.open.add(w(__dev.D.tree.root).i); }")
        page.evaluate("() => __dev.select(null)"); page.wait_for_timeout(300)
        dots = page.evaluate("() => [...document.querySelectorAll('.dvt .row .dvchd')].map(d => d.closest('.row').querySelector('.dtg').textContent)")
        assert dots == ["h1"], dots
        # S-50: ⌥R reloads the page in Dev Studio, the board stays; ⌘R is not taken (the app's menu has no key for it, a browser reloads)
        g = page.evaluate("__dev.D.gen"); blur(page); page.keyboard.press("Alt+KeyR"); page.wait_for_timeout(1500)
        assert page.evaluate("() => window.__board === 1 && !!__dev.D && __dev.D.gen > " + str(g)), "⌥R did not reload the page in Dev Studio"
        g = page.evaluate("__dev.D.gen")
        assert page.evaluate("""() => { const e = new KeyboardEvent('keydown', { key: 'r', code: 'KeyR', metaKey: true, cancelable: true, bubbles: true });
          dispatchEvent(e); return e.defaultPrevented; }""") is False, "Dev Studio took ⌘R"
        page.wait_for_timeout(600); assert page.evaluate("__dev.D.gen") == g
        assert "⌥R" in page.evaluate("() => { const b = document.querySelector('.dvui hy-studio-actions [data-a=reload]'); return (b.title || '') + (b.dataset.key || ''); }")
        # ⌥R typed in the page itself (its agent): the page again
        sb = next(fr for fr in page.frames if "/sandbox/" in fr.url)
        sb.evaluate("() => document.body.dispatchEvent(new KeyboardEvent('keydown', { key: '®', code: 'KeyR', altKey: true, bubbles: true, cancelable: true }))")
        page.wait_for_function("() => __dev.D && __dev.D.gen > " + str(g), timeout=8000); page.wait_for_function("() => __dev.D.tree", timeout=10000)
        # S-41: the file gone, Reload says so
        f.rename(lib / "site/gone.html")
        page.click(".dvui hy-studio-actions [data-a=reload]"); page.wait_for_function("() => __dev.D && __dev.D.info.none", timeout=12000)
        assert "did not answer" in page.inner_text(".dvt")
        # S-28: ⌘↵ is Done
        blur(page); page.keyboard.press("Meta+Enter"); page.wait_for_function("() => !__dev.D", timeout=5000)
        assert not errors, errors
        br.close()
