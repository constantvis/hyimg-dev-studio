"""Dev Studio's interface as the owner meets it, Chromium, dark (owner 2026-10-09 on a screenshot of Dev Studio: «глючит, когда ты первый
раз открываешь, ты не можешь ничего нажать. Только Escape помогает ... нужно какие-то тесты запустить, чтобы протестировать Dev-режим, и
чтобы Dev-режим соответствовал нашему дизайну»; an arrow at the dock: «размеры элементов внизу не соответствуют»).

- The first open, as in the app: the board inside the library page, the app's user agent, so Hyimg's drag band (ui/dragband.js) runs and
  tells the app where the window drags from. Every control of the studio takes its click without an Esc first: the top-right actions,
  a dock tool, a tree row, the search. The cause of the freeze: the band took the actions in the top row for background, since their
  root (.dvui) has no box of its own, and the app dragged the window under Done, Reload and Open.
- Each dock tool, the top-right actions (Reload, the split «Open in browser» and its menu, Done), picking in the tree, the Comment tool,
  and Esc stepping out one thing at a time.
- The geometry: the dock's buttons are Image Studio's tools in the dock (one size, no ground, the separator), the dock itself and its
  switch the Board's; the right block wears the block header (A · Line) as 3D Studio's and Image Studio's do, the search the 3D outline's.
HYIMG_REPO=<hyimg checkout> python3 -m pytest tests/test_dev_ui.py"""
import json

from playwright.sync_api import sync_playwright

from test_dev_studio import board, hy  # noqa: F401

CEF = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/154.0 Safari/537.36 HyimgCEF/1"
MID = "(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"
DOCKB = "#dock .dvbar button.hy-dkb"   # the dock's icon buttons (Hyimg's one dock, 2026-10-10: the view % and Actions beside them)


def enter(page, card="h1"):
    page.dblclick(f".plg[data-id={card}]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000); page.wait_for_timeout(300)


def dark(page):
    page.evaluate("() => { setPref('theme', 'dark'); renderBg(); }")


def test_first_open_in_the_app_takes_every_click_without_esc(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1400, "height": 900}, color_scheme="dark", user_agent=CEF)
        page = ctx.new_page(); errors, band = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: band.append(json.loads(m.text[10:])) if m.text.startswith('HYIMG_MSG:{"action":"dragband"') else None)
        page.goto(f"http://127.0.0.1:{port}/?view=canvas")
        page.wait_for_selector("#cvFrame")
        for _ in range(200):
            cv = next((f for f in page.frames if "/canvas" in f.url), None)
            if cv: break
            page.wait_for_timeout(100)
        cv.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
        page.wait_for_timeout(600)
        off = page.evaluate("() => { const r = document.getElementById('cvFrame').getBoundingClientRect(); return [r.left, r.top]; }")
        at = lambda s: (lambda q: (off[0] + q[0], off[1] + q[1]))(cv.evaluate(MID, s))   # noqa: E731
        # the first open of the session, by a double click on the card as the owner does
        page.mouse.dblclick(*at(".plg[data-id=h1]"))
        cv.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000); page.wait_for_timeout(400)
        page.evaluate("() => hyDragScan()")
        assert band, "the drag band was never sent"
        b = band[-1]

        def clickable(s):   # under the window's drag band and in none of its holes: the app drags the window, the page never gets the click
            x, y = at(s)
            return y >= b["h"] or any(h[0] <= x <= h[0] + h[2] and h[1] <= y <= h[1] + h[3] for h in b["holes"])
        controls = [".dvui hy-studio-actions [data-a=reload]", ".dvui hy-open-in .oi-go", ".dvui hy-open-in .oi-more", ".dvui hy-studio-actions [data-a=done]",
                    "#dock .dvbar [data-tool=pick]", ".dvl [data-q]", ".dvt .row"]
        lost = [s for s in controls if not clickable(s)]
        assert not lost, (lost, b)
        # and the clicks do what they say, no Esc pressed before: a dock tool, a tree row, Reload, then Done
        page.mouse.click(*at("#dock .dvbar [data-tool=pick]"))
        cv.wait_for_function("() => __dev.D.picking", timeout=3000)
        page.mouse.click(*at(".dvt .row:nth-child(3)"))
        cv.wait_for_function("() => __dev.D.sel !== null && document.querySelector('.dvt .row.sel')", timeout=3000)
        gen = cv.evaluate("__dev.D.gen")
        page.mouse.click(*at(".dvui hy-studio-actions [data-a=reload]"))
        cv.wait_for_function(f"() => __dev.D.gen === {gen + 1} && __dev.D.tree", timeout=20000)
        page.mouse.click(*at(".dvui hy-studio-actions [data-a=done]"))
        cv.wait_for_function("() => !__dev.D", timeout=5000)
        assert not errors, errors
        br.close()


def test_dock_tools_each_take_their_click(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port); dark(page); enter(page)
        # no Draw: Hyimg's drawing tools wait for later (owner 2026-10-09, hyimg docs/LATER.md)
        # Actions is one of them too: Hyimg's icon button, its name and ⌘K in the tooltip (studios audit S-01, 2026-10-11)
        assert page.evaluate(f"() => [...document.querySelectorAll('{DOCKB}')].map(b => b.dataset.tool || b.dataset.a)") == ["pick", "comment", "undo", "redo", "acts"]
        assert page.locator(f"{DOCKB}[data-tool=comment]").get_attribute("aria-label") == "Annotation"
        # each one is what the pointer finds at its middle: nothing lies over the dock
        top = page.evaluate(f"""() => [...document.querySelectorAll('{DOCKB}')].map(b => {{ const r = b.getBoundingClientRect();
          const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!e && b.contains(e); }})""")
        assert all(top), top
        on = lambda t: page.evaluate(f"() => document.querySelector('{DOCKB}[data-tool={t}]').classList.contains('on')")   # noqa: E731
        page.click(f"{DOCKB}[data-tool=pick]"); assert page.evaluate("__dev.D.picking") and on("pick")
        page.click(f"{DOCKB}[data-tool=pick]"); assert not page.evaluate("__dev.D.picking") and not on("pick")
        page.click(f"{DOCKB}[data-tool=comment]"); assert page.evaluate("__dev.D.commenting") and on("comment") and not on("pick")
        page.click(f"{DOCKB}[data-tool=comment]"); assert not page.evaluate("__dev.D.commenting")
        page.mouse.move(700, 450); page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("p"); page.wait_for_timeout(150)   # P draws nothing
        assert page.evaluate("() => !hyAnnot.active && !document.querySelector('#dock .ann-bar, [data-tool=pen]')")
        # nothing written yet: Undo and Redo are off, and still there
        assert page.evaluate(f"() => [...document.querySelectorAll('{DOCKB}[data-a=undo], {DOCKB}[data-a=redo]')].map(b => b.disabled)") == [True, True]
        assert page.evaluate("!!__dev.D"), "P left the studio"
        assert not errors, errors
        br.close()


def test_tree_pick_comment_and_esc_one_step_at_a_time(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port); dark(page); enter(page)
        # a row of the tree picks its element: the row chosen, the inspector on it
        page.click(".dvt .row[aria-level='3'] .nm")
        page.wait_for_function("() => __dev.D.sel !== null && __dev.D.detail", timeout=5000)
        tag = page.evaluate("__dev.D.detail.t")
        assert page.inner_text(".dvr .ih b") == tag and page.evaluate("() => document.querySelectorAll('.dvt .row.sel').length") == 1
        # C: the Comment tool, its button on; Esc gives back the tool before it and keeps the selection
        page.mouse.move(700, 450); page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("c"); assert page.evaluate("__dev.D.commenting")
        page.keyboard.press("Escape"); assert page.evaluate("[!!__dev.D, !!__dev.D.commenting, __dev.D.sels.size]") == [True, False, 1]
        # Esc: the selection goes, the studio stays; Esc again leaves it
        page.keyboard.press("Escape"); assert page.evaluate("[!!__dev.D, __dev.D.sels.size, document.querySelectorAll('.dvt .row.sel').length]") == [True, 0, 0]
        page.keyboard.press("Escape"); page.wait_for_function("() => !__dev.D && !document.querySelector('.dvui')", timeout=5000)
        assert not errors, errors
        br.close()


def test_open_in_browser_is_a_split_button_with_a_menu(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port); dark(page); enter(page)
        # no Mac app to ask: «Open in browser», its chevron behind a hairline all the same, the menu the default browser alone
        split = ("() => { const e = document.querySelector('.dvui hy-open-in'), m = e.querySelector('.oi-more'); "
                 "return [e.querySelector('.oi-go').textContent, !m.hidden, Math.round(m.getBoundingClientRect().width), getComputedStyle(m).borderLeftWidth]; }")
        assert page.evaluate(split) == ["Open in browser", True, 30, "1px"], page.evaluate(split)
        page.click(".dvui hy-open-in .oi-more"); page.wait_for_selector(".hy-oi-menu [data-b]")
        rows = "() => [...document.querySelectorAll('.hy-oi-menu [data-b]')].map(b => [b.dataset.b, b.textContent.trim(), b.getAttribute('aria-checked')])"
        assert page.evaluate(rows) == [["", "Default browser", "true"]], page.evaluate(rows)
        with page.context.expect_page() as tab:
            page.click(".hy-oi-menu [data-b]")
        assert "/sandbox/" in tab.value.url and tab.value.url.endswith("/site/index.html"), tab.value.url
        tab.value.close()
        assert page.evaluate("[!!__dev.D, !!document.querySelector('.hy-oi-menu')]") == [True, False]
        assert not errors, errors
        br.close()


# the app's browsers (native/Browsers.swift) through a stand-in: each with its icon, as the app sends them, a 1 × 1 PNG
ICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
STUB = """(icon) => { window.SENT = []; hyBrowsers.via(m => { SENT.push(m);
  if (m.op === 'list') setTimeout(() => hyimgBrowsers({ op: 'list', default: 'com.apple.Safari', last: '', browsers: [
    { id: 'org.mozilla.firefox', name: 'Firefox', icon }, { id: 'com.apple.Safari', name: 'Safari', icon }] }));
  return true; }); }"""


def test_open_in_names_the_apps_browser_with_its_icon(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port); dark(page)
        page.evaluate(STUB, ICON); enter(page)
        page.wait_for_function("() => document.querySelector('.dvui hy-open-in .oi-go').textContent === 'Open in Safari'", timeout=5000)
        go = page.evaluate("() => { const i = document.querySelector('.dvui hy-open-in .oi-go img'); return i && [i.getAttribute('src'), Math.round(i.getBoundingClientRect().width)]; }")
        assert go == [ICON, 18], go
        page.click(".dvui hy-open-in .oi-more"); page.wait_for_selector(".hy-oi-menu [data-b]")
        rows = page.evaluate("() => [...document.querySelectorAll('.hy-oi-menu [data-b]')]"
                             ".map(b => [b.querySelector('.oi-n').textContent, !!b.querySelector('img.oi-ic'), b.getAttribute('aria-checked')])")
        assert rows == [["Firefox", True, "false"], ["Safari", True, "true"]], rows
        page.keyboard.press("Escape"); assert page.evaluate("[!!__dev.D, !!document.querySelector('.hy-oi-menu')]") == [True, False]
        assert not errors, errors
        br.close()


# one button's look: its box, corners, ground, icon; a separator's box; the dock and its switch
BTN = """(s) => { const b = document.querySelector(s); if (!b) return null;
  const r = b.getBoundingClientRect(), c = getComputedStyle(b), i = b.querySelector('svg'), ir = i && i.getBoundingClientRect();
  return { w: Math.round(r.width), h: Math.round(r.height), r: c.borderRadius, bg: c.backgroundColor, pad: c.paddingLeft, icon: ir ? Math.round(ir.width) : 0 }; }"""
SEP = """(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(), c = getComputedStyle(e);
  return [Math.round(r.width), Math.round(r.height), c.backgroundColor, c.marginLeft, c.marginRight]; }"""
DOCK = """() => { const d = document.getElementById('dock'), c = getComputedStyle(d), m = document.getElementById('modes'), mr = m.getBoundingClientRect();
  return { h: Math.round(d.getBoundingClientRect().height), pad: c.paddingTop, gap: c.gap, r: c.borderRadius, bg: c.backgroundColor, bd: c.borderTopWidth + ' ' + c.borderTopColor,
    modes: [Math.round(mr.width), Math.round(mr.height), ...[...m.querySelectorAll('button')].map(b => Math.round(b.getBoundingClientRect().width))] }; }"""
BLOCK = """(s) => { const out = {}; for (const [k, q] of Object.entries(s)) { const e = document.querySelector(q); if (!e) { out[k] = null; continue; }
  const r = e.getBoundingClientRect(), c = getComputedStyle(e);
  out[k] = [Math.round(r.height), c.borderRadius, c.backgroundColor, c.fontSize, c.fontWeight, c.paddingLeft, c.paddingRight, c.color]; } return out; }"""


def test_geometry_matches_the_board_and_the_other_studios(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port); dark(page); page.wait_for_timeout(300)
        board_dock = page.evaluate(DOCK)
        enter(page)
        dev_dock = page.evaluate(DOCK)
        dev = {t: page.evaluate(BTN, f"{DOCKB}[data-{'tool' if t in ('pick', 'comment') else 'a'}={t}]") for t in ("pick", "comment", "undo", "redo")}
        dev_sep = page.evaluate(SEP, "#dock .dvbar .sep")
        dev_blk = page.evaluate(BLOCK, {"search": ".dvl .hy-search > input", "sh": ".dvl .hy-sh", "row": ".dvt .row", "bh": ".dvr .hy-bh", "tab": ".dvr .hy-bh-tab", "blk": ".dvr"})
        # the dock and its switch are the Board's; every button of Dev Studio's dock one size, one look (owner: «размеры ... не соответствуют»)
        # in a Studio the switch is Board and that Studio alone (studios audit S-01, 2026-10-11), its segments the Board's size
        assert {k: v for k, v in dev_dock.items() if k not in ("w", "modes")} == {k: v for k, v in board_dock.items() if k != "modes"}, (dev_dock, board_dock)
        assert [w for w in dev_dock["modes"][2:] if w] == board_dock["modes"][2:4] and dev_dock["modes"][1] == board_dock["modes"][1], (dev_dock, board_dock)
        assert len({json.dumps(v) for v in dev.values()}) == 1, dev
        assert dev["pick"]["h"] == 34 and dev["pick"]["icon"] == 17 and dev["pick"]["r"] == "999px", dev["pick"]
        # the block header and its one title: 34 px, a 24 px tab on its plate, as every block's (Hyimg ui/hy/block.css)
        assert dev_blk["bh"][0] == 34 and dev_blk["tab"][0] == 24 and dev_blk["tab"][3] == "12.5px", dev_blk
        page.keyboard.press("Escape"); page.wait_for_function("() => !__dev.D", timeout=5000)
        frames = page.evaluate("() => PLGST.some(x => x.name === 'frames' && x.ok)")
        if frames:   # Image Studio's tools in the dock: the contract Dev Studio's dock follows
            page.dblclick(".it[data-id=i0]"); page.wait_for_function("() => document.querySelector('#dock .plgdock button.ifg')", timeout=30000); page.wait_for_timeout(500)
            img = page.evaluate(BTN, "#dock .plgdock button.ifg:not(.on)")
            img_on = page.evaluate(BTN, "#dock .plgdock button.ifg.on")
            img_sep = page.evaluate(SEP, "#dock .plgdock .sep")
            img_dock = page.evaluate(DOCK)
            assert {k: dev["pick"][k] for k in ("w", "h", "r", "bg", "pad", "icon")} == img, (dev["pick"], img)
            assert img_on["w"] == dev["pick"]["w"] and dev_sep == img_sep, (img_on, dev_sep, img_sep)
            assert {k: v for k, v in img_dock.items() if k != "modes"} == {k: v for k, v in dev_dock.items() if k != "modes"}, (img_dock, dev_dock)
            assert [w for w in img_dock["modes"] if w] == [w for w in dev_dock["modes"] if w], (img_dock, dev_dock)
            page.click("#modes [data-mode=board]"); page.wait_for_function("() => !__frames.ED", timeout=10000)
        if page.evaluate("() => PLGST.some(x => x.name === '3d' && x.ok)"):   # 3D Studio's blocks: its search, its section heads, its block header
            page.evaluate("() => { sel = new Set(['m1']); render(); MODES.enter('3d', ['m1']); }")
            page.wait_for_selector(".m3r .hy-bh-tab", timeout=30000); page.wait_for_timeout(400)
            d3 = page.evaluate(BLOCK, {"search": ".m3l .hy-search > input", "sh": ".m3l .hy-sh", "row": ".m3l .row", "bh": ".m3r .hy-bh", "tab": ".m3r .hy-bh-tab.on", "blk": ".m3r"})
            for k in ("search", "sh", "bh"):
                assert dev_blk[k] == d3[k], (k, dev_blk[k], d3[k])
            assert dev_blk["blk"][1:] == d3["blk"][1:], (dev_blk["blk"], d3["blk"])   # its height follows where the dock stands, not the contract
            assert dev_blk["tab"][:5] == d3["tab"][:5] and dev_blk["row"][:3] == d3["row"][:3], (dev_blk, d3)
        assert not errors, errors
        br.close()
