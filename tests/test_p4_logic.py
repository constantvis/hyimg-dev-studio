"""Dev Studio's critical and high findings of the П4 logic audit (2026-10-10, hyimg docs/process.md §5), each as the person meets it.
Chromium, the dark theme, a temporary library:

- S-06 the board's keys wait while Dev Studio is open: L, 3, ⇧1, ⌘A, ⌘D, ⌘X leave the board as it was
- S-07 ⌘Z with nothing of Dev's to take back does not undo the board behind it
- S-24 an undo or a redo the server refuses keeps its step, and a redo says «Can't redo»
- S-05 typing in place after the file changed outside: the change outside stays, the page shows the file, a toast says why
- S-18 Esc in the inspector's colour field cancels, nothing is written
- S-19 a letter typed while the weight's menu has the focus writes no font-weight
- S-17 a change still settling (↑ in a number field) and a text being typed are written when Done comes at once

  HYIMG_REPO=<Hyimg checkout> nice -n 10 python3 -m pytest tests/test_p4_logic.py
"""
import json

from playwright.sync_api import sync_playwright

from test_dev_edit import ed, click_in, picked, file_is  # noqa: F401  (ed is the fixture)

HOOK = "() => { window.__T = []; const o = window.hyToast; window.hyToast = (t, k, x) => { window.__T.push([String(t), k || '']); return o && o(t, k, x); }; }"
BOARD = """() => JSON.stringify({ n: Object.keys(board.items).sort(), x: Object.fromEntries(Object.entries(board.items).map(([k, i]) => [k, [i.x, i.y, i.opacity ?? 1]])),
  groups: Object.keys(board.groups).length, cam: [Math.round(cam.x), Math.round(cam.y), +cam.z.toFixed(3)], past: past.length })"""


def open_board(p, port):
    br = p.chromium.launch(); page = br.new_page(viewport={"width": 1500, "height": 950}, color_scheme="dark")
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
    page.evaluate(HOOK)
    return br, page, errors


def open_dev(page):
    page.dblclick(".plg[data-id=e1]")
    page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.rev", timeout=20000)
    frame = next(fr for fr in page.frames if "/sandbox/" in fr.url)
    frame.wait_for_function("() => document.getElementById('dyn')")
    last = None
    for _ in range(40):   # the camera's flight between the panels has ended
        page.wait_for_timeout(150); b = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
        if b == last: break
        last = b
    if not page.evaluate("__dev.D.picking"): page.click(".dvbar [data-tool=pick]"); page.wait_for_function("() => __dev.D.picking")
    return frame


def blur(page): page.evaluate("document.activeElement && document.activeElement.blur()")


def toasts(page): return page.evaluate("() => window.__T.splice(0)")


def test_keys_and_undo_stay_in_dev_studio(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        # a board step before the Studio: a note beside the card
        page.evaluate("() => { const b = snap(); board.items.n1 = { type: 'note', text: 'before', x: 800, y: 0, w: 200, h: 120 }; commit(b); render(); }")
        page.wait_for_timeout(300)
        frame = open_dev(page); blur(page)
        b0 = page.evaluate(BOARD)
        # S-07: nothing of Dev's to take back, ⌘Z leaves the board's note where it is
        page.keyboard.press("Meta+z"); page.wait_for_timeout(500)
        assert page.evaluate(BOARD) == b0 and page.evaluate("!!board.items.n1"), "⌘Z in Dev Studio undid the board"
        # S-06: the board's keys wait
        for k in ("l", "3", "Shift+Digit1", "Meta+a", "Meta+d", "Meta+x"):
            blur(page); page.keyboard.press(k); page.wait_for_timeout(250)
            assert page.evaluate(BOARD) == b0, f"{k} changed the board behind Dev Studio"
        assert page.evaluate("!!__dev.D"), "Dev Studio stays open"
        # S-24: an edit, its undo refused (the file changed outside since), the step stays; a refused redo says so
        click_in(page, frame, "#title"); picked(page, "h1")
        page.fill(".dvr input[data-c='background-color']", "#ff0000"); page.press(".dvr input[data-c='background-color']", "Enter")
        try: page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000)
        except Exception: raise AssertionError(json.dumps([toasts(page), page.evaluate("[__dev.D.rev, __dev.D.detail && __dev.D.detail.src, __dev.D.srcErr]"), f.read_text()[:300]]))
        page.wait_for_timeout(600); written = f.read_bytes()
        f.write_bytes(written + b"<!-- outside -->"); toasts(page)
        blur(page); page.keyboard.press("Meta+z"); page.wait_for_timeout(1200)
        assert page.evaluate("[__dev.D.past.length, __dev.D.future.length]") == [1, 0], "a refused undo keeps its step"
        assert any("Can't undo" in t for t, _k in toasts(page))
        f.write_bytes(written); page.keyboard.press("Meta+z")   # the file as the step left it: the undo goes through
        page.wait_for_function("() => __dev.D.future.length === 1", timeout=8000); page.wait_for_timeout(600)
        f.write_bytes(f.read_bytes() + b"<!-- outside again -->"); toasts(page)
        page.keyboard.press("Meta+Shift+z"); page.wait_for_timeout(1200)
        assert page.evaluate("[__dev.D.past.length, __dev.D.future.length]") == [0, 1], "a refused redo keeps its step"
        said = [t for t, _k in toasts(page)]
        assert any("Can't redo" in t for t in said) and not any("Can't undo" in t for t in said), said
        assert not errors, errors
        br.close()


def test_outside_change_esc_and_the_weight_menu(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        frame = open_dev(page)
        # S-18: a colour typed, then Esc: nothing written, the field as it was
        click_in(page, frame, "#title"); picked(page, "h1")
        fld = ".dvr input[data-c='background-color']"; was = page.input_value(fld)
        page.fill(fld, "#00ff00"); page.press(fld, "Escape"); page.wait_for_timeout(1200)
        assert f.read_bytes() == orig, "Esc in the colour field wrote it"
        assert page.input_value(fld) == was
        # S-19: letters with the weight's menu focused write no font-weight
        page.focus(".dvr select[data-w]")
        for k in ("b", "l", "t", "e"): page.keyboard.press(k)
        page.wait_for_timeout(1200)
        assert b"font-weight" not in f.read_bytes(), "a letter on the weight's menu wrote font-weight"
        blur(page)
        # S-05: typing starts, the file's text changes outside meanwhile, the typing ends: the change outside stays
        click_in(page, frame, "#lead", dbl=True)
        frame.wait_for_function("() => document.getElementById('lead').isContentEditable")
        outside = orig.replace(b'<p id="lead">Some text</p>', b'<p id="lead">Outside text</p>')
        f.write_bytes(outside); toasts(page)
        page.keyboard.type("Mine"); page.keyboard.press("Enter"); page.wait_for_timeout(2500)
        assert f.read_bytes() == outside, "the edit overwrote the change made outside"
        assert any("changed meanwhile" in t for t, _k in toasts(page))
        frame = next(fr for fr in page.frames if "/sandbox/" in fr.url)
        frame.wait_for_function("() => document.getElementById('lead') && document.getElementById('lead').textContent === 'Outside text'", timeout=10000)
        assert not errors, errors
        br.close()


def test_done_writes_what_is_still_settling(ed):
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        frame = open_dev(page)
        # S-17: ↑ ↑ in Corners, Done at once
        click_in(page, frame, "#hero"); picked(page, "section")
        s = ".dvr input[data-n=border-radius]"; v0 = float(page.input_value(s) or 0)
        page.focus(s); page.keyboard.press("ArrowUp"); page.keyboard.press("ArrowUp")
        page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D", timeout=10000)
        want = f"border-radius: {v0 + 2:g}px".encode()
        assert want in f.read_bytes(), f.read_bytes().decode()
        # a text being typed, then Done
        frame = open_dev(page)
        click_in(page, frame, "#lead", dbl=True)
        frame.wait_for_function("() => document.getElementById('lead').isContentEditable")
        page.keyboard.type("Typed"); page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D", timeout=10000)
        assert b'<p id="lead">Typed</p>' in f.read_bytes(), f.read_bytes().decode()
        assert not errors, errors
        br.close()
