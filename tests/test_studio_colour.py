"""Dev Studio wears its colour (owner 2026-10-09, «конечно» to «3D Studio и Dev Studio пока остаются синими. Дать им их цвета?»), the green
of the owner's glossary of modes (--dev), as Image Studio wears its purple (hyimg-frames 6e04f1a) and 3D Studio its pink: inside the studio
the chosen Dev segment of the dock's switch, the picked row of the tree, the chosen weight in the inspector, the tool in hand and the
primary Done are in the green, Done and the tool with white marks, Reload as it was; the tree's tag, id and class colours stay the code's;
back on the board the Board segment is the selection's blue again. Chromium, dark, the classic look.
"""
from playwright.sync_api import sync_playwright

from test_dev_studio import board, hy  # noqa: F401

PROBE = """([v, prop]) => { const p = document.createElement('i'); p.style.setProperty(prop, v); document.body.append(p);
  const c = getComputedStyle(p).getPropertyValue(prop); p.remove(); return c; }"""
SEG = "() => { const b = document.querySelector('#dock #modes > button[aria-pressed=true]'); return [b.dataset.mode, getComputedStyle(b).color]; }"
BTN = "(s) => { const c = getComputedStyle(document.querySelector(s)); return [c.backgroundColor, c.color]; }"
CODE = "() => ['.dvt .dia', '.dvt .dic'].map(s => { const e = document.querySelector(s); return e ? getComputedStyle(e).color : null; })"


def settle(page, want):
    """the chosen segment and its colour once it has eased (.2 s from whenever the switch caught up), or what it is after 3 s"""
    try: page.wait_for_function(f"(w) => JSON.stringify(({SEG})()) === JSON.stringify(w)", arg=want, timeout=3000)
    except Exception: pass
    assert page.evaluate(SEG) == want, page.evaluate(SEG)


def test_dev_studio_wears_its_colour(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.evaluate("() => { setPref('theme', 'dark'); renderBg(); }")
        assert page.evaluate("() => [document.documentElement.dataset.theme, document.documentElement.dataset.ui]") == ["dark", "classic"]
        green, blue = page.evaluate(PROBE, ["#2fae6a", "color"]), page.evaluate(PROBE, ["var(--sel)", "color"])
        assert green != blue, (green, blue)

        page.dblclick(".plg[data-id=h1]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        settle(page, ["dev", green])   # the switch's chosen segment: Dev Studio's green
        # the tree's code colours are the code's own, not the Studio's
        assert page.evaluate(CODE) == [page.evaluate(PROBE, ["#e8a24a", "color"]), page.evaluate(PROBE, ["#7dbbf5", "color"])]
        # the picked row: a fill and a line of the green, the app's selected row
        page.click(".dvt .row:has(.dtg:text-is('main')) .chev"); page.click(".dvt .row:has(.dtg:text-is('section')) .chev")
        page.click(".dvt .row:has(.dia:text-is('#t'))"); page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'h1'")
        row = page.evaluate("() => getComputedStyle(document.querySelector('.dvt .row.sel')).backgroundColor")
        assert row == page.evaluate(PROBE, ["color-mix(in srgb, #2fae6a 14%, transparent)", "background-color"]), row
        # the inspector's chosen weight: on the Studio's plate, not the grey one
        page.wait_for_selector(".dvr hy-segmented[data-w] > :is(.st, button.on)", timeout=5000)
        plate = page.evaluate("() => getComputedStyle(document.querySelector('.dvr hy-segmented[data-w] > .st') || "
                              "document.querySelector('.dvr hy-segmented[data-w] > button.on')).backgroundColor")
        assert plate == page.evaluate(PROBE, ["color-mix(in srgb, #2fae6a 30%, var(--hy-well))", "background-color"]), plate
        # the tool in hand in the dock and Done top right: filled with the green, white on it; Reload as it was
        page.click("#dock .dvbar [data-tool=pick]"); page.wait_for_function("() => __dev.D.picking"); page.wait_for_timeout(300)
        assert page.evaluate(BTN, "#dock .dvbar [data-tool=pick]") == [green, "rgb(255, 255, 255)"]
        assert page.evaluate(BTN, "hy-studio-actions [data-a=done]") == [green, "rgb(255, 255, 255)"]
        assert page.evaluate(BTN, "hy-studio-actions [data-a=reload]")[0] != green
        # back on the board: Board chosen, in the selection's blue
        page.click("hy-studio-actions [data-a=done]"); page.wait_for_function("() => !__dev.D && !document.querySelector('.dvui')")
        settle(page, ["board", blue])
        assert not errors, errors
        br.close()
