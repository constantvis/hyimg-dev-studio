"""HTML cards stay sharp when zoomed in (owner 2026-10-08: «не всегда рендерится в высоком разрешении, справа мазня, не видно что
там»: two cards side by side at 153 % on a Retina screen, the left one live, the right one a 640 px still blown up to 2200 device px).

The live pages go to the cards big on screen, the ones nearest the centre first; a card outside the screen never holds one of the four,
and a card that lost its page gets it back when one frees. At rest a card's still matches its size on screen in device pixels: 640, 1280
or 2560 (the page drawn at twice its css size), the sharper one fades in over the one shown.

  HYIMG_REPO=<Hyimg checkout> nice -n 10 python3 -m pytest tests/test_live_sharp.py
"""
import json

from playwright.sync_api import sync_playwright

from test_dev_studio import hy   # noqa: F401 (the fixture)

# fine print in two colours, so a blurred still and a sharp one tell apart in the screenshots
PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{n}</title><style>body{{margin:0;background:#15161a;color:#e8e8ea;
font:13px/1.35 system-ui}} h1{{font-size:56px;margin:24px 32px 8px}} p{{margin:4px 32px;font-size:11px;color:#9aa}} .g{{display:grid;
grid-template-columns:repeat(6,1fr);gap:10px;padding:16px 32px}} .g div{{border:1px solid #3a3d44;border-radius:8px;padding:8px;font-size:10px}}
</style></head><body><h1>Card {n}</h1>{rows}<div class="g">{cells}</div></body></html>"""
ROW, COL = 620, 800   # the owner's group «Figma · раунд 6»: 720 × 450 cards, 80 apart across, 170 down


def page_html(n):
    rows = "".join(f"<p>{n}.{k} The quick brown fox jumps over the lazy dog, 0123456789 — fine print that a blurred still smears.</p>" for k in range(8))
    return PAGE.format(n=n, rows=rows, cells="".join(f"<div>cell {n}.{k}<br>label · 12 px</div>" for k in range(24)))


def grid(lib, state, cols=3, rows=3):
    """cols × rows HTML cards in board order row by row, as the owner's board has them"""
    (lib / "r6").mkdir(exist_ok=True)
    items = {}
    for k in range(cols * rows):
        (lib / "r6" / f"c{k}.html").write_text(page_html(k))
        items[f"c{k}"] = {"type": "html", "src": f"r6/c{k}.html", "vw": 1440, "x": (k % cols) * COL, "y": (k // cols) * ROW, "w": 720, "h": 450,
                          "pics": [f"r6/c{k}.html"]}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 3, "items": items, "groups": {}, "removed": {}}))
    return items


def open_board(p, port, size=(1800, 1000)):
    br = p.chromium.launch()
    page = br.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=2, color_scheme="dark")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
    return br, page, errors


STATE = """() => Object.fromEntries([...document.querySelectorAll('.plg[data-type=html]')].map(el => {
  const img = el.querySelector('img.dvi:not(.dvo)'), f = el.querySelector('iframe.dvpg');
  return [el.dataset.id, { live: !!f && el.classList.contains('pv'), frame: !!f, hidden: el.hidden, still: img ? (img.currentSrc || img.src) : '',
    nat: img ? img.naturalWidth : 0 }]; }))"""
# the cards' stills asked for since t0 (performance.now())
SEEN = "t0 => performance.getEntriesByType('resource').filter(e => e.startTime >= t0).map(e => e.name).filter(u => u.includes('/thumb?') && u.includes('r6%2F'))"


def on_screen(page, ids):
    """each card's width on screen in device px and whether it is in the view at all"""
    return page.evaluate("""ids => { const r = stage.getBoundingClientRect(), dpr = devicePixelRatio;
      return Object.fromEntries(ids.map(id => { const b = document.querySelector(`.plg[data-id='${id}']`).getBoundingClientRect();
        const vis = b.right > r.left && b.left < r.right && b.bottom > r.top && b.top < r.bottom; return [id, { dev: Math.round(b.width * dpr), vis }]; })); }""", ids)


def settle(page, ms=2500):
    page.wait_for_timeout(ms)


def test_two_cards_side_by_side_at_150_on_retina_are_both_live_or_sharp(hy, tmp_path):
    port, lib, state = hy
    grid(lib, state)
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        # the middle row's first two cards (the owner's c4 and c4b) fill the screen, the rows above and below lie just off it
        page.evaluate(f"HY.camera(60, {ROW - 120}, 1.53, false)")
        # a fresh library: Chromium draws the 9 pages first, the browser's six connections wait on them, so this may take seconds
        page.wait_for_function(f"() => ['c3', 'c4'].every(id => ({STATE})()[id].live || ({STATE})()[id].nat >= 2400)", timeout=30000)
        s, scr = page.evaluate(STATE), on_screen(page, ["c3", "c4"])
        page.screenshot(path=str(tmp_path / "150.png"))
        assert scr["c3"]["vis"] and scr["c4"]["vis"], scr
        for id in ("c3", "c4"):
            assert s[id]["live"] or s[id]["nat"] >= 2400, (id, s[id], scr[id])
        # nothing off screen holds a live page
        vis = on_screen(page, list(s))
        assert not [id for id, v in s.items() if v["frame"] and not vis[id]["vis"]], (s, vis)
        assert not errors, errors
        br.close()


def test_a_card_outside_the_screen_never_takes_a_live_page_from_one_on_it(hy):
    port, lib, state = hy
    grid(lib, state, cols=6, rows=2)
    live = lambda: sorted(id for id, v in page.evaluate(STATE).items() if v["frame"])
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        # at 100 % two cards of the second row fill the screen; the first row's, first in the board's order, lie just above it, inside the
        # board's view pass (half a screen around): before 2026-10-08 c0, c1, c2 and c6 took the four pages and c7 on screen got none
        page.evaluate(f"HY.camera(-40, {ROW - 20}, 1, false)")
        page.wait_for_function("() => ['c6', 'c7'].every(id => document.querySelector(`.plg[data-id=${id}] iframe.dvpg`))", timeout=20000)
        settle(page, 500)
        assert live() == ["c6", "c7"], (live(), page.evaluate("__dev.C.dbg"), page.evaluate("HY.cam"), on_screen(page, ["c0", "c1", "c6", "c7"]))
        # a pan up while it moves starts nothing and keeps what runs; once it stops the first row's cards take the pages, the second's go
        during = page.evaluate(f"""async () => {{ const seen = new Set();
          for (let k = 1; k <= 30; k++) {{ HY.camera(-40, {ROW - 20} - k * {2 * ROW / 30}, 1, true); await new Promise(r => requestAnimationFrame(r));
            document.querySelectorAll('.plg iframe.dvpg').forEach(f => seen.add(f.parentElement.dataset.id)); }}
          return [...seen].sort(); }}""")
        assert during == ["c6", "c7"], during
        page.wait_for_function("() => ['c0', 'c1'].every(id => document.querySelector(`.plg[data-id=${id}] iframe.dvpg`))", timeout=600)
        assert live() == ["c0", "c1"]
        # a card that got no page because four nearer ones had them gets one when one of them goes
        page.evaluate("HY.camera(-40, -20, 0.62, false)"); settle(page, 1500)   # 2 rows × 3 cards on screen, 446 px each: 4 of 6 live
        first = live()
        assert len(first) == 4 and all(id in ("c0", "c1", "c2", "c6", "c7", "c8") for id in first), first
        gone = first[0]
        page.evaluate(f"() => {{ delete board.items['{gone}']; render(); }}"); settle(page, 800)
        assert len(live()) == 4 and gone not in live(), live()
        assert not errors, errors
        br.close()


def test_the_still_asked_matches_the_size_on_screen_and_zooming_out_fetches_no_big_one(hy):
    port, lib, state = hy
    grid(lib, state)
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        cases = [(0.2, 640), (0.6, 1280), (1.53, 2560)]   # 720 board units × zoom × 2 device px: 288, 864, 2203
        for z, want in cases:
            page.evaluate(f"HY.camera(0, 0, {z}, false)")
            page.wait_for_function(f"() => document.querySelector('.plg[data-id=c0]')._s === {want}", timeout=3000)
            # the sharper still shows once the server drew it (the first pictures of a fresh library take Chromium a few seconds)
            page.wait_for_function(f"() => {{ const i = document.querySelector('.plg[data-id=c0] img.dvi:not(.dvo)'); return /[?&]s={want}&vw=1440&vh=900$/.test(i.src) && i.naturalWidth; }}",
                                   timeout=30000)
            nat = page.evaluate("document.querySelector('.plg[data-id=c0] img.dvi:not(.dvo)').naturalWidth")
            assert nat == want, (z, nat)   # 2560 too: the page is drawn at twice its css size
        # zoomed out the cards step down to 640 and ask for nothing bigger, the cards that come into view included
        t0 = page.evaluate("performance.now()")
        page.evaluate("HY.camera(0, 0, 0.3, false)"); settle(page, 1500)
        page.evaluate("HY.camera(0, 0, 0.1, false)"); settle(page, 1500)
        seen = page.evaluate(SEEN, t0)
        assert not [u for u in seen if "s=2560" in u or "s=1280" in u], seen   # the 640 ones come from the browser's cache mostly
        assert page.evaluate("[...document.querySelectorAll('.plg[data-type=html]')].every(el => !el._s || el._s === 640)")
        assert not errors, errors
        br.close()


MARK = """<!doctype html><html><body style="margin:0;background:#15161a"><div style="position:absolute;left:calc(50% - 600px);top:120px;width:48px;
height:300px;background:#f00"></div><h1 style="color:#eee;margin:0;padding:24px;font:600 40px system-ui">Layout</h1></body></html>"""


def red_left(png):
    """where the red bar starts across the shot, as a share of its width"""
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(png)).convert("RGB"); w, h = im.size; px = im.load()
    xs = [x for x in range(w) for y in range(0, h, 8) if px[x, y][0] > 200 and px[x, y][1] < 60]
    return min(xs) / w if xs else None


def test_a_1440_cards_still_lays_out_as_its_live_page(hy):
    """the still is drawn at the card's own viewport: a 1440 card drawn at 1280 put this bar at 40/1280 of the width, its page at 120/1440"""
    port, lib, state = hy
    (lib / "m.html").write_text(MARK)
    items = {"m": {"type": "html", "src": "m.html", "vw": 1440, "x": 0, "y": 0, "w": 720, "h": 450, "pics": ["m.html"]}}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 3, "items": items, "groups": {}, "removed": {}}))
    with sync_playwright() as p:
        br, page, errors = open_board(p, port)
        page.evaluate("HY.camera(-60, -60, 1, false)")
        page.wait_for_function("() => document.querySelector('.plg[data-id=m]').classList.contains('pv')", timeout=20000)
        page.wait_for_timeout(800)
        card = page.locator(".plg[data-id=m]")
        live = red_left(card.screenshot())
        page.evaluate("document.querySelector('.plg[data-id=m] iframe.dvpg').style.visibility = 'hidden'")
        page.wait_for_function("() => { const i = document.querySelector('.plg[data-id=m] img.dvi:not(.dvo)'); return /vw=1440&vh=900/.test(i.src) && i.naturalWidth; }",
                               timeout=30000)
        page.wait_for_timeout(400)
        still = red_left(card.screenshot())
        assert live is not None and still is not None, (live, still)
        assert abs(live - 120 / 1440) < 0.006 and abs(still - live) < 0.006, (live, still)
        assert not errors, errors
        br.close()
