"""Dev Studio has no board blue left (owner 2026-10-09, the element picked in the live page drawn in blue: «опять мы что-то выделяем, у нас
это синего цвета вместо зеленого. Давай еще раз проверь цвета, чтобы у нас все режимы соответствовали»). While the studio is open its
colour is the window's: Hyimg's switch puts it on the root (hyimg ui/modes.js, data-studio and --hy-studio), so --sel, --hy-sel and the
notes' info colour are the green. The test walks every visible element of the board's window (and its ::before and ::after) with a row
picked, a row hovered, the select tool in hand and an info note up, and finds no computed colour equal to a board blue; the live page's
marks (agent.js: the hover's fill and line, the pick's line, the label «tag.class w × h») are the green, set by the board. Back on the
board the selection is blue again. Chromium, dark.
"""
from playwright.sync_api import sync_playwright

from test_dev_studio import board, hy  # noqa: F401

# the board's blues: the selection (--sel dark #3b82f6, light #2563eb) and the notes' info (#0a84ff, light #007aff), any alpha, in the two
# forms Chromium gives a computed colour (rgb() and, from color-mix, color(srgb …))
WALK = """() => {
  const BLUE = [[59, 130, 246], [37, 99, 235], [10, 132, 255], [0, 122, 255]];
  const rgbs = s => [...s.matchAll(/rgba?\\(([^)]*)\\)/g)].map(m => m[1].split(/[\\s,\\/]+/).filter(Boolean).slice(0, 3).map(Number))
    .concat([...s.matchAll(/color\\(srgb ([^)]*)\\)/g)].map(m => m[1].split(/[\\s\\/]+/).filter(Boolean).slice(0, 3).map(x => +x * 255)));
  const blue = s => rgbs(s).some(c => BLUE.some(b => b.every((x, i) => Math.abs(x - c[i]) < 2.5)));
  const seen = el => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = getComputedStyle(e); if (s.opacity === '0' || s.visibility === 'hidden') return false; } return true; };
  const name = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + [...el.classList].slice(0, 3).map(c => '.' + c).join('');
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect(); if (!r.width || !r.height || r.right < 0 || r.bottom < 0 || r.left > innerWidth || r.top > innerHeight || !seen(el)) continue;
    const text = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) || el instanceof SVGElement;
    for (const ps of [null, '::before', '::after']) {
      const s = getComputedStyle(el, ps); if (ps && (s.content === 'none' || s.content === 'normal')) continue;
      const props = ['background-color', 'background-image', 'box-shadow', 'fill', 'stroke'];
      if (text || ps) props.push('color');
      if (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth)) props.push('outline-color');
      for (const sd of ['top', 'right', 'bottom', 'left']) if (parseFloat(s.getPropertyValue(`border-${sd}-width`))) props.push(`border-${sd}-color`);
      for (const p of props) { const v = s.getPropertyValue(p); if (v && blue(v)) out.push([name(el) + (ps || ''), p, v]); }
    }
  }
  return out;
}"""
PROBE = """([v, prop]) => { const p = document.createElement('i'); p.style.setProperty(prop, v); document.body.append(p);
  const c = getComputedStyle(p).getPropertyValue(prop); p.remove(); return c; }"""
# the live page's marks live in a closed shadow root: the test opens it, in the page's frame only, before agent.js runs
OPEN_MARKS = """(() => { const a = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (o) { return a.call(this, this.localName === 'hy-dev-marks' ? Object.assign({}, o, { mode: 'open' }) : o); }; })();"""
MARKS = """() => { const R = document.querySelector('hy-dev-marks').shadowRoot, g = (s, p) => getComputedStyle(R.querySelector(s)).getPropertyValue(p);
  return { hover: g('.h', 'background-color'), hoverLine: g('.h', 'outline-color'), pick: g('.s', 'outline-color'), label: g('.l', 'background-color'),
    labelInk: g('.l', 'color'), shown: [...R.querySelectorAll('.h, .s, .l')].map(e => getComputedStyle(e).display) }; }"""


def test_dev_studio_has_no_board_blue(hy):  # noqa: F811
    port, lib, state = hy
    with sync_playwright() as p:
        br, page, errors = board(p, port)
        page.context.add_init_script(OPEN_MARKS)
        page.evaluate("() => { setPref('theme', 'dark'); renderBg(); }")
        green = page.evaluate(PROBE, ["#2fae6a", "color"])
        blue = page.evaluate(PROBE, ["var(--sel)", "color"])
        assert blue == "rgb(59, 130, 246)", blue

        page.dblclick(".plg[data-id=h1]"); page.wait_for_function("() => __dev.D && __dev.D.tree", timeout=20000)
        # a row picked and another hovered, the select tool in hand, an info note up
        page.click(".dvt .row:has(.dtg:text-is('main')) .chev"); page.click(".dvt .row:has(.dtg:text-is('section')) .chev")
        page.click(".dvt .row:has(.dia:text-is('#t'))"); page.wait_for_function("() => __dev.D.detail && __dev.D.detail.t === 'h1'")
        page.click("#dock .dvbar [data-tool=pick]"); page.wait_for_function("() => __dev.D.picking")
        page.evaluate("() => hyToast('Dev Studio: a note', 'info')")
        page.hover(".dvt .row:has(.dtg:text-is('section'))"); page.wait_for_timeout(500)
        found = page.evaluate(WALK); assert found == [], "\n".join(" ".join(f) for f in found)
        assert page.evaluate("() => document.documentElement.dataset.studio") == "dev"
        assert page.evaluate(PROBE, ["var(--sel)", "color"]) == green   # the root's selection colour is the Studio's while it is open
        note = page.evaluate("() => { const n = document.querySelector('#hyToasts .ht:not(.error):not(.success):not(.warn)'); return getComputedStyle(n).color; }")
        assert note == green, note

        # the live page's marks: the hovered section's fill and line, the picked h1's line, the label, all the green; white words on it
        fr = next(f for f in page.frames if "/sandbox/" in f.url)
        fr.wait_for_function("() => { const h = document.querySelector('hy-dev-marks'); return h && h.shadowRoot }", timeout=5000)
        m = fr.evaluate(MARKS)
        g = green[4:-1]
        assert m["shown"] == ["block", "block", "block"], m
        assert m["hover"] == f"rgba({g}, 0.16)" or m["hover"] == fr.evaluate(PROBE, ["color-mix(in srgb, #2fae6a 16%, transparent)", "background-color"]), m
        assert m["hoverLine"].replace(" ", "") in (f"rgba({g},0.95)".replace(" ", ""), fr.evaluate(PROBE, ["color-mix(in srgb, #2fae6a 95%, transparent)", "outline-color"]).replace(" ", "")), m
        assert m["pick"] == green and m["label"] == green and m["labelInk"] == "rgb(255, 255, 255)", m

        # back on the board (its segment of the switch): the board's blue comes back on the root
        page.click("#dock #modes > button[data-mode=board]")
        page.wait_for_function("() => !__dev.D", timeout=5000)
        page.wait_for_function("() => !document.documentElement.dataset.studio", timeout=3000)
        assert page.evaluate(PROBE, ["var(--sel)", "color"]) == blue
        assert not errors, errors
        br.close()
