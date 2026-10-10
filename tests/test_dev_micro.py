"""Dev Studio wears Hyimg's micro primitives (review/ui/hy, core bf07b4b; round 15's micro sheet r15-micro.html, owner 2026-10-09:
«Все топ, все делай»; round 16's scrub r16-scrub.html, version A, owner 2026-10-10: «отлично, беру»). On a disposable library, Chromium,
the dark theme:

- each place uses the primitive, none of the plugin's own looks: Edit in the block's header is <hy-minitoggle>, the file's light
  <hy-led> (a ring before the first write, the Studio's green after it), «This element | Everywhere» <hy-segmented variant=micro>, the
  inspector's number fields drag by their label (scrub()), a written row wears .hy-dot, the tree row's + and bin are .hy-ri on a .hy-hovrow
- scrubbing W: the page follows the drag, nothing is written while the button is held, the file takes it once as it ends, one step of
  ⌘Z, which brings the first bytes back; ⇧ ten times, ⌥ a tenth; Esc while dragging puts the value back and writes nothing; a click on
  the letter types the number, Esc puts it back, Enter writes it
- keyboard and ARIA: the toggle is a switch Space turns over, the segments a radiogroup the arrows choose in, the LED an image named by
  what it says, the fields named by their label

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_micro.py
"""
from playwright.sync_api import sync_playwright

from test_dev_edit import PAGE, click_in, ed, file_is, picked, shot  # noqa: F401
from test_dev_editmode import blur, ready, studio

PROBE = """([v, prop]) => { const p = document.createElement('i'); p.style.setProperty(prop, v); document.body.append(p);
  const c = getComputedStyle(p).getPropertyValue(prop); p.remove(); return c; }"""
MID = "(e) => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"
FIELDS = {"width": "W", "height": "H", "padding": "Padding", "gap": "Gap", "border-radius": "Corners", "filter": "Blur", "font-size": "Size",
          "border-width": "Width"}


def hero(page, frame):
    """the section.card#hero picked: its fill comes from --purple, it is a flex box neither (Gap off)"""
    if not page.evaluate("__dev.D.picking"):
        blur(page); page.keyboard.press("i"); page.wait_for_function("() => __dev.D.picking")
    click_in(page, frame, "#hero"); picked(page, "section"); ready(page, "section")


def width_of(frame):
    return frame.evaluate("() => parseFloat(getComputedStyle(document.getElementById('hero')).width)")


def drag(page, sel, dx, steps=6, hold=0, mods=()):
    """the label sel dragged dx px to the right; hold: ms the button stays down halfway, before the rest of the move"""
    x, y = page.locator(sel).evaluate(MID)
    page.mouse.move(x, y); page.mouse.down()
    for k in mods: page.keyboard.down(k)
    half = steps // 2
    for i in range(1, half + 1): page.mouse.move(x + dx * i / steps, y)
    if hold: page.wait_for_timeout(hold)
    out = page.evaluate("() => [__dev.D.past.length, __dev.D.dirty]")
    for i in range(half + 1, steps + 1): page.mouse.move(x + dx * i / steps, y)
    for k in mods: page.keyboard.up(k)
    page.mouse.up()
    return out


def test_each_place_wears_the_micro_primitive(ed):  # noqa: F811
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        green = page.evaluate(PROBE, ["#2fae6a", "background-color"])
        # 1 · Edit in the block's header: the mini toggle, a 20 × 11 track, its checkbox a switch named Edit; on, the track in the green
        mt = page.locator(".dvr .hy-bh hy-minitoggle[data-edit]")
        assert mt.count() == 1 and page.locator(".dvr .dvmt i, .dvr button[data-edit]").count() == 0
        got = mt.evaluate("""m => { const b = getComputedStyle(m, '::before'), i = m.querySelector('input');
          return [Math.round(m.getBoundingClientRect().height), parseFloat(b.width), parseFloat(b.height), i.type, i.getAttribute('role'), i.getAttribute('aria-label'),
            i.checked, Math.round(i.getBoundingClientRect().height)]; }""")
        assert got == [22, 20, 11, "checkbox", "switch", "Edit", False, 24], got
        mt.click(); page.wait_for_function("() => __dev.D.edit"); page.wait_for_timeout(300)   # the track's colour eases in .15 s
        assert mt.evaluate("m => [m.hasAttribute('checked'), m.querySelector('input').checked, getComputedStyle(m, '::before').backgroundColor]") == [True, True, green]
        mt.click(); page.wait_for_function("() => !__dev.D.edit")

        # 4 · the file's LED: hy-led, 6 px, flat; a ring before the first write
        led = page.locator(".dvr .ih hy-led.dvled")
        assert led.count() == 1 and page.locator(".dvr span.dvled").count() == 0
        got = led.evaluate("l => { const s = getComputedStyle(l), r = l.getBoundingClientRect(); return [l.getAttribute('state'), l.dataset.s, Math.round(r.width), "
                           "Math.round(r.height), s.backgroundColor, s.boxShadow.includes('inset'), l.getAttribute('role'), l.getAttribute('aria-label')]; }")
        assert got[:7] == ["off", "idle", 6, 6, "rgba(0, 0, 0, 0)", True, "img"] and got[7], got

        # 3 · «This element | Everywhere» of a colour from a custom property: the micro segments, 18 px options in a 22 px well
        hero(page, frame)
        seg = page.locator(".dvr hy-segmented[data-s='background-color']")
        got = seg.evaluate("""s => [s.getAttribute('variant'), Math.round(s.getBoundingClientRect().height),
          [...s.querySelectorAll(':scope > button')].map(b => Math.round(b.getBoundingClientRect().height)), s.getAttribute('role')]""")
        assert got == ["micro", 22, [18, 18], "radiogroup"], got

        # 5 · the number fields: each label is the scrub's handle (ew-resize), its field named by it; Gap of a box that is not flex has none
        got = page.evaluate("""() => [...document.querySelectorAll('.dvr .dnf')].map(l => { const h = l.querySelector('.dnl'), i = l.querySelector('input');
          return [l.dataset.p, h.textContent, h.classList.contains('hy-scrub-h'), getComputedStyle(h).cursor, i.getAttribute('aria-label')]; })""")
        by = {g[0]: g[1:] for g in got}
        assert set(by) == set(FIELDS), by
        for prop, label in FIELDS.items():
            if prop == "gap": assert by[prop][:2] == ["Gap", False], by[prop]; continue
            assert by[prop] == [label, True, "ew-resize", label], (prop, by[prop])

        # 7 · a written row wears Hyimg's change dot in the green; 8 · in Edit mode the hovered row shows + and the bin as .hy-ri
        drag(page, ".dvr .dnf[data-p=width] .dnl", 30)
        page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000)
        dot = page.locator(".dvt .row.sel .hy-dot")
        page.wait_for_function("() => document.querySelector('.dvt .row.sel .hy-dot')", timeout=5000)
        assert dot.evaluate("d => [Math.round(d.getBoundingClientRect().width), getComputedStyle(d).backgroundColor]") == [5, green]
        page.wait_for_function("() => document.querySelector('.dvr .ih hy-led.dvled').getAttribute('state') === 'on'", timeout=8000)
        assert led.evaluate("l => getComputedStyle(l).backgroundColor") == green
        mt.click(); page.wait_for_function("() => __dev.D.edit")
        page.mouse.move(5, 5); page.wait_for_timeout(200)
        row = page.locator(".dvt .row.sel"); row.hover(); page.wait_for_timeout(350)
        got = row.evaluate("""r => [r.classList.contains('hy-hovrow'), [...r.querySelectorAll('.hy-ri')].map(b => [b.classList.contains('dvea') ? '+' : 'bin',
          Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().height), +getComputedStyle(b).opacity, b.getAttribute('aria-label')])]""")
        assert got[0] and [g[:4] for g in got[1]] == [["+", 20, 20, 1], ["bin", 20, 20, 1]] and all(g[4] for g in got[1]), got
        assert page.locator(".dvt hy-icon-button.dvea, .dvt hy-icon-button.dved").count() == 0
        # the plugin's own looks are gone
        css = page.evaluate("() => [...document.querySelectorAll('style')].map(s => s.textContent).join('\\n')")
        for old in (".dvmt i", "dvled[data-s", "hy-segmented.dvms >", "@keyframes dvled", "background: var(--dev); }   /* changed"):
            assert old not in css, old
        shot(page, "dev-micro-dark.png")
        assert not errors, errors
        br.close()


def test_scrubbing_w_writes_once_a_drag_and_undoes_in_one_step(ed):  # noqa: F811
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        hero(page, frame)
        w0 = width_of(frame); W = ".dvr .dnf[data-p=width] .dnl"
        assert page.input_value(".dvr .dnf[data-p=width] input") == ""   # «auto»
        # a slow drag: the page follows, the file waits while the button is held (longer than the inspector's settle of 450 ms)
        past, _ = drag(page, W, 40, steps=8, hold=900)
        assert past == 0, "nothing is written while the letter is held"
        page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000); page.wait_for_timeout(700)
        assert page.evaluate("__dev.D.past.length") == 1, "one write for the drag"
        w1 = round(w0 + 40)
        assert width_of(frame) == w1
        file_is(f, orig.replace(b'<section class="card" id="hero">', f'<section class="card" id="hero" style="width: {w1}px">'.encode()))
        page.wait_for_function(f"() => document.querySelector('.dvr .dnf[data-p=width] input').value === '{w1}'", timeout=5000)
        # ⌘Z: the file as it was, the page too, in one step
        blur(page); page.keyboard.press("Meta+z"); file_is(f, orig)
        frame.wait_for_function(f"() => parseFloat(getComputedStyle(document.getElementById('hero')).width) === {w0}")

        # ⇧ ten times faster, ⌥ ten times finer
        ready(page, "section")
        drag(page, W, 6, steps=3, mods=("Shift",))
        page.wait_for_function("() => __dev.D.past.length === 1", timeout=8000)
        frame.wait_for_function(f"() => parseFloat(getComputedStyle(document.getElementById('hero')).width) === {w0 + 60}")
        ready(page, "section"); page.wait_for_function(f"() => document.querySelector('.dvr .dnf[data-p=width] input').value === '{round(w0 + 60)}'")
        drag(page, W, 20, steps=4, mods=("Alt",))
        page.wait_for_function("() => __dev.D.past.length === 2", timeout=8000)
        frame.wait_for_function(f"() => Math.abs(parseFloat(getComputedStyle(document.getElementById('hero')).width) - {w0 + 62}) < .01")

        # Esc while dragging: the value back in the page and the field, nothing written, Dev Studio still open
        ready(page, "section"); before = f.read_bytes(); wb = width_of(frame)
        x, y = page.locator(W).evaluate(MID)
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + 15, y, steps=3); page.mouse.move(x + 30, y, steps=3)
        assert width_of(frame) == wb + 30
        page.keyboard.press("Escape"); page.mouse.up(); page.wait_for_timeout(800)
        assert page.evaluate("[!!__dev.D, __dev.D.past.length]") == [True, 2] and f.read_bytes() == before and width_of(frame) == wb

        # a click on the letter types: Esc puts the number back and writes nothing, Enter writes it
        page.locator(W).click(); page.wait_for_function("() => document.activeElement === document.querySelector('.dvr .dnf[data-p=width] input')")
        page.keyboard.type("333"); page.keyboard.press("Escape"); page.wait_for_timeout(700)
        assert f.read_bytes() == before and width_of(frame) == wb
        assert page.input_value(".dvr .dnf[data-p=width] input") == str(round(w0 + 62, 1)).removesuffix(".0")
        page.locator(W).click(); page.keyboard.type("333"); page.keyboard.press("Enter")
        page.wait_for_function("() => __dev.D.past.length === 3", timeout=8000)
        assert width_of(frame) == 333
        assert not errors, errors
        br.close()


def test_keyboard_and_aria(ed):  # noqa: F811
    port, lib, state, tmp = ed
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        # the mini toggle: Tab-able, Space turns Edit mode on and off
        page.locator(".dvr hy-minitoggle[data-edit] input").focus(); page.keyboard.press("Space")
        page.wait_for_function("() => __dev.D.edit")
        page.keyboard.press("Space"); page.wait_for_function("() => !__dev.D.edit")
        # the LED names what it says
        assert page.get_attribute(".dvr .ih hy-led", "aria-label") == "Edits go into the file as you make them"
        # the micro segments: a radiogroup, the arrows choose
        hero(page, frame)
        seg = ".dvr hy-segmented[data-s='background-color']"
        page.locator(f"{seg} button[value=el]").focus(); page.keyboard.press("ArrowRight")
        page.wait_for_function("() => __dev.D.scope['background-color'] === 'all'")
        page.wait_for_selector(f"{seg}[value=all]")
        assert page.get_attribute(f"{seg} button[value=all]", "aria-checked") == "true"
        # a number field: ↑ steps it, its label drags it, its name is its label
        ready(page, "section")
        inp = ".dvr .dnf[data-p=border-radius] input"
        assert page.get_attribute(inp, "aria-label") == "Corners" and page.get_attribute(".dvr .dnf[data-p=border-radius] .dnl", "aria-hidden") == "true"
        page.focus(inp); page.keyboard.press("ArrowUp")
        frame.wait_for_function("() => getComputedStyle(document.getElementById('hero')).borderTopLeftRadius === '13px'")
        assert not errors, errors
        br.close()
