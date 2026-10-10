"""Dev Studio's session actions top right (owner 2026-10-09 on the dock where Reload, Open and Done stood beside the tools: «кнопки Done у
нас всегда стандартизированы справа вверху, а не внизу ... Что такое Open? Может быть, Open in browser тогда нужно написать»): Hyimg's one
element for them (ui/hy/actions.js) in the studio's root. Reload, Open in browser and Done stand at the top row's right end (no round buttons in a Studio),
Done last in the studio's green with white words; the dock keeps the tools, Undo, Redo and the switch only. Without the Mac app «Open in
browser» opens the page alone, sandboxed, in a new tab; with the app's browsers (a stand-in through hyBrowsers.via) it names the default and
its menu opens the page in another one; Esc in that menu closes the menu and leaves the studio open, Esc after it leaves. Done leaves and
takes the actions away. A frames plugin's HTML frame also offers its Live view there, before Reload. Chromium, dark."""
from playwright.sync_api import sync_playwright

from test_dev_studio import board, hy  # noqa: F401

PROBE = "(v) => { const p = document.createElement('i'); p.style.color = v; document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }"
BOX = "(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.height)]; }"
ACTS = "() => [...document.querySelectorAll('.dvui hy-studio-actions > *')].map(b => b.dataset.a)"
DOCK = "() => [...document.querySelectorAll('#dock .dvbar [data-a], #dock .dvbar [data-tool]')].map(b => b.dataset.a || b.dataset.tool)"
GO = "() => document.querySelector('.dvui hy-open-in .oi-go').textContent"
STUB = """() => { window.SENT = []; hyBrowsers.via(m => { SENT.push(m);
  if (m.op === 'list') setTimeout(() => hyimgBrowsers({ op: 'list', default: 'com.apple.Safari', last: '', browsers: [
    { id: 'org.mozilla.firefox', name: 'Firefox', icon: '' }, { id: 'com.apple.Safari', name: 'Safari', icon: '' }] }));
  return true; }); }"""


def enter(page, card="h1"):
    page.dblclick(f".plg[data-id={card}]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000); page.wait_for_timeout(400)


def test_dev_studio_actions_top_right(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.evaluate("() => { setPref('theme', 'dark'); renderBg(); }")
        enter(page)
        # Reload, Open in browser, Done; none of them in the dock any more
        assert page.evaluate(ACTS) == ["reload", "open", "done"]
        assert page.evaluate(DOCK) == ["pick", "comment", "undo", "redo", "acts"], page.evaluate(DOCK)   # no Draw (hyimg docs/LATER.md); Actions ⌘K (2026-10-10)
        assert page.evaluate("() => !!document.querySelector('#dock #modes')")
        # the top row's line and height, at its gutter: in a Studio the board's round buttons are away (owner 2026-10-09 on round 14's
        # 3D Studio: «В режиме студии мы вот эти все элементы убираем»)
        acts, width = page.evaluate(BOX, ".dvui hy-studio-actions"), page.evaluate("() => innerWidth")
        assert acts[1] == 12 and acts[3] == 38 and acts[2] == width - 12, (acts, width)
        assert page.evaluate("() => ['#bntf', '#bkeys', '#bhist', '#bset'].every(q => !document.querySelector(q).getClientRects().length)")
        # Done: the studio's green, white words, the key in its tooltip; Reload on the row's glass
        green = page.evaluate(PROBE, "#2fae6a")
        done = page.evaluate("() => { const b = document.querySelector('.dvui hy-studio-actions [data-a=done]'), c = getComputedStyle(b); return [c.backgroundColor, c.color, b.title]; }")
        assert done == [green, "rgb(255, 255, 255)", "Done · ⌘↵ or Esc"], done   # ⌘↵ is the primary everywhere (P4 S-28)
        assert page.evaluate("() => getComputedStyle(document.querySelector('.dvui hy-studio-actions [data-a=reload]')).backgroundColor") != green
        # no Mac app: «Open in browser», the page alone, still sandboxed, in a new tab
        assert page.evaluate(GO) == "Open in browser"
        with page.context.expect_page() as tab:
            page.click(".dvui hy-open-in .oi-go")
        url = tab.value.url
        assert "/sandbox/" in url and url.endswith("/site/index.html"), url
        tab.value.close()
        # Done leaves the studio, the actions go with it
        page.click(".dvui hy-studio-actions [data-a=done]")
        page.wait_for_function("() => !__dev.D && !document.querySelector('hy-studio-actions')", timeout=5000)
        assert not errors, errors
        br.close()


def test_dev_studio_open_in_a_browser_of_the_app(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.evaluate(STUB); enter(page)
        page.wait_for_function(f"() => ({GO})() === 'Open in Safari'", timeout=5000)
        page.click(".dvui hy-open-in .oi-more"); page.wait_for_selector(".hy-oi-menu [data-b]")
        # Esc closes the menu, the studio stays; the next Esc leaves it
        page.keyboard.press("Escape"); page.wait_for_timeout(200)
        assert page.evaluate("() => [!!document.querySelector('.hy-oi-menu'), !!__dev.D]") == [False, True]
        page.click(".dvui hy-open-in .oi-more"); page.click(".hy-oi-menu [data-b='org.mozilla.firefox']")
        sent = [m for m in page.evaluate("SENT") if m["op"] == "open"]
        assert len(sent) == 1 and sent[0]["app"] == "org.mozilla.firefox" and "/sandbox/" in sent[0]["url"] and sent[0]["url"].endswith("/site/index.html"), sent
        assert page.evaluate(GO) == "Open in Firefox" and len(page.context.pages) == 1
        page.keyboard.press("Escape"); page.wait_for_function("() => !__dev.D", timeout=5000)
        assert not errors, errors
        br.close()


def test_html_frame_offers_its_live_view_first(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        if not page.evaluate("() => PLGST.some(x => x.name === 'frames' && x.ok)"):
            br.close(); return   # the frames plugin is not beside this one
        page.evaluate("""() => { const b = HY.snap(); board.items.f1 = { type: 'htmlframe', src: 'site/index.html', vw: 1280, x: 0, y: 900, w: 640, h: 400 };
          HY.commit(b); }""")
        page.wait_for_selector(".plg[data-id=f1]"); enter(page, "f1")
        assert page.evaluate(ACTS) == ["live", "reload", "open", "done"]
        page.click(".dvui hy-studio-actions [data-a=live]")
        page.wait_for_function("() => !__dev.D && document.querySelector('.plg[data-id=f1].plg-live')", timeout=10000)
        assert not errors, errors
        br.close()
