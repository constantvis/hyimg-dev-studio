"""The inspector's number fields in Russian (studios audit S-03, 2026-10-11: «Зазор24», «Разме16», «Толщин0», the Russian words ran under
the number). Hyimg's one rule for a scrub: the handle is a letter or an icon no wider than 20 px, never a word; the word is the handle's
tooltip and the field's name for a screen reader. Every pixel field shows its px, Gap too. On a disposable library, Chromium, the dark theme.

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_handles.py
"""
import json

from playwright.sync_api import sync_playwright

from test_dev_edit import PAGE, click_in, ed, picked  # noqa: F401
from test_dev_editmode import blur, ready, studio

WORDS = {"width": "W", "height": "H", "padding": "Отступы", "gap": "Зазор", "border-radius": "Углы", "filter": "Размытие", "font-size": "Размер",
         "border-width": "Толщина"}
FIELDS = """() => [...document.querySelectorAll('.dvr .dnf')].map(l => {
  const h = l.querySelector('.dnl'), i = l.querySelector('input'), r = h.getBoundingClientRect(), u = l.querySelector('.du');
  const text = document.createRange(); text.selectNodeContents(h);
  return { p: l.dataset.p, text: h.textContent.trim(), svg: !!h.querySelector('svg'), title: h.title, aria: i.getAttribute('aria-label'),
    w: Math.round(r.width), right: r.right, start: i.getBoundingClientRect().left + parseFloat(getComputedStyle(i).paddingLeft),
    ink: text.getBoundingClientRect().width, unit: u ? u.textContent : '', scrub: h.classList.contains('hy-scrub-h') }; })"""


def test_handles_are_letters_or_icons_in_russian(ed):  # noqa: F811
    port, lib, state, tmp = ed
    (tmp / "settings.json").write_text(json.dumps({"cv.lang": "ru", "cv.theme": "dark"}))
    # the hero a flex box, so Gap is on and shows its number
    (lib / "site/edit.html").write_text(PAGE.replace(".card { background:", ".card { display: flex; gap: 18px; background:"))
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        blur(page); page.keyboard.press("i"); page.wait_for_function("() => __dev.D.picking")
        click_in(page, frame, "#hero"); picked(page, "section"); ready(page, "section")
        got = {f["p"]: f for f in page.evaluate(FIELDS)}
        assert set(got) == set(WORDS), got
        bad = []
        for prop, word in WORDS.items():
            f = got[prop]
            if prop in ("width", "height"):
                if f["text"] != word: bad.append(f"{prop}: the handle is «{f['text']}», not its letter")
            elif f["text"] or not f["svg"]: bad.append(f"{prop}: the handle is «{f['text']}», not an icon")
            if f["w"] > 20: bad.append(f"{prop}: the handle is {f['w']} px wide")
            if f["right"] > f["start"] + 0.5: bad.append(f"{prop}: the handle runs under the number ({f['right']:.1f} > {f['start']:.1f})")
            if f["aria"] != word: bad.append(f"{prop}: the field is named «{f['aria']}»")
            if prop not in ("width", "height") and f["title"] != word: bad.append(f"{prop}: the handle's tooltip is «{f['title']}»")
            if not f["scrub"]: bad.append(f"{prop}: the handle does not drag the number")
        if got["gap"]["unit"] != "px": bad.append(f"gap: no px after its number: {got['gap']}")
        assert not bad, "\n".join(bad)
        assert page.input_value(".dvr .dnf[data-p=gap] input") == "18"
        assert not errors, errors
        br.close()
