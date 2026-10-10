"""Dev Studio's right block of round 15 and its Edit mode (owner 2026-10-09 on r15/r15-dev.html, «Inspector · History»: «Да, неплохо,
делай. Только я бы еще добавил режим редактирования HTML. Чтобы мы могли, как в браузере в инспекторе можно редактировать, так же и тут ...
Может быть, переключать туда-сюда»). On a disposable library, Chromium, the dark theme:

- Inspect and Edit: the mini toggle in the block's header and E turn Edit mode on and off; Select comes on with it and goes back after
- in Edit mode a text typed in the tree, an attribute and an inline style typed in the inspector show in the page and land in the file,
  only that node's bytes changed; Esc cancels a field and nothing is written; ⌘Z takes each back, History lists them and goes back to one
- a tag renamed in the tree and an element deleted with ⌫: start and end tag, the element's line; ⌘Z puts the element back in the page
- a double click on a text in the page types it with Select off; the tree shows the new text; a script's element can't be edited
- the block as round 15 draws it: the header's 34 px and its standard 24 px tabs 8 px in, the crumbs row of 46 px with its 30 px tile,
  the 6 px LED in the studio's green once the file was written, no line under the header

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_dev_editmode.py
"""
import json

from playwright.sync_api import sync_playwright

from test_dev_edit import PAGE, click_in, ed, file_is, picked, shot, splice  # noqa: F401

HEADER = '<header id="top"><h1 id="title">Hello world</h1></header>'


def studio(p, port):
    br = p.chromium.launch(); page = br.new_page(viewport={"width": 1500, "height": 950}, color_scheme="dark")
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas.html")
    page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok)", timeout=30000)
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.dblclick(".plg[data-id=e1]")
    page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.rev", timeout=20000)
    frame = next(fr for fr in page.frames if "/sandbox/" in fr.url)
    frame.wait_for_function("() => document.getElementById('dyn')")
    last = None
    for _ in range(40):   # the camera's flight between the panels has ended
        page.wait_for_timeout(150); b = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
        if b == last: break
        last = b
    return br, page, frame, errors


# the Edit toggle (Hyimg's <hy-minitoggle>): its checked attribute and its checkbox
ON = "() => { const m = document.querySelector('.dvr .hy-bh hy-minitoggle[data-edit]'); return [m.hasAttribute('checked'), m.querySelector('input').checked]; }"


def blur(page):
    page.evaluate("document.activeElement && document.activeElement.blur()"); page.mouse.move(760, 900)


def ready(page, tag):
    """the picked element's detail for the file's revision now"""
    page.wait_for_function(f"""() => {{ const d = __dev.D.detail; return d && d.t === {json.dumps(tag)} && d.src && (d.src.why || d.src.rev === __dev.D.rev) }}""", timeout=8000)


def history(page):
    page.click(".dvr [data-tab=hist]")
    rows = page.evaluate("() => [...document.querySelectorAll('.dvr .dvhl .dvhr')].map(r => [r.querySelector('.dvh-w').textContent, !r.classList.contains('undone')])")
    page.click(".dvr [data-tab=insp]")
    return rows


def test_edit_mode_toggles_and_writes_each_change_in_place(ed):  # noqa: F811
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        # Inspect, as the studio opens: the toggle off, the page takes the clicks
        assert page.evaluate("[__dev.D.edit, __dev.D.picking]") == [False, False]
        assert page.evaluate(ON) == [False, False]
        # E: Edit mode, Select with it; E again: Inspect, Select as it was; the toggle does the same
        blur(page); page.keyboard.press("e")
        page.wait_for_function("() => __dev.D.edit && __dev.D.picking && document.querySelector('.dvui').classList.contains('dvedit-on')")
        assert page.evaluate(ON) == [True, True]
        page.keyboard.press("e"); page.wait_for_function("() => !__dev.D.edit && !__dev.D.picking")
        page.click(".dvr .hy-bh [data-edit]"); page.wait_for_function("() => __dev.D.edit && __dev.D.picking")
        assert page.evaluate("!!__dev.D") and f.read_bytes() == orig

        # 1. the h1's text, double-clicked in the tree: a field in the row, Enter writes the text and only it
        click_in(page, frame, "#title"); picked(page, "h1", "Hello world")
        page.dblclick(".dvt .row.sel .dtx"); page.wait_for_selector(".dvt .row .dvin")
        assert page.input_value(".dvt .row .dvin") == "Hello world"
        page.fill(".dvt .row .dvin", "Hi there"); page.press(".dvt .row .dvin", "Enter")
        want1 = PAGE.replace(HEADER, '<header id="top"><h1 id="title">Hi there</h1></header>').encode()
        file_is(f, want1)
        assert frame.evaluate("document.getElementById('title').textContent") == "Hi there"
        page.wait_for_selector(".dvt .row.sel .dtx:text-is('Hi there')")
        assert page.locator(".dvt .row.sel .hy-dot").count() == 1, "the row of a changed element wears the change dot"

        # Esc in a name (the tag) cancels: the field goes, nothing is written, the page keeps its text (a text's Esc keeps what was typed,
        # owner decision 2026-10-10, P4 S-25: hyimg tests/test_p4_studio_keys.py)
        ready(page, "h1")
        page.dblclick(".dvt .row.sel .dtg"); page.wait_for_selector(".dvt .row .dvin")
        page.fill(".dvt .row .dvin", "nope"); page.press(".dvt .row .dvin", "Escape")
        page.wait_for_function("() => !document.querySelector('.dvt .row .dvin')"); page.wait_for_timeout(600)
        assert f.read_bytes() == want1 and frame.evaluate("document.getElementById('title').textContent") == "Hi there"

        # 2. an attribute in the inspector's Attributes: the page follows as you type, Esc puts it back, Enter writes only its value
        ready(page, "h1")
        idv = ".dvr .dattr .dva[data-a=id] .dva-v"
        page.fill(idv, "headline")
        frame.wait_for_function("() => !!document.getElementById('headline')")
        page.press(idv, "Escape")
        frame.wait_for_function("() => !!document.getElementById('title') && !document.getElementById('headline')")
        page.wait_for_timeout(500); assert f.read_bytes() == want1
        ready(page, "h1"); page.fill(idv, "headline"); page.press(idv, "Enter")
        want2 = want1.decode().replace('<h1 id="title">', '<h1 id="headline">').encode()
        file_is(f, want2)
        page.wait_for_selector(".dvt .row.sel .dia:text-is('#headline')")

        # 3. an inline style: added with + as name="value", then typed in its own field; the page and the file follow
        ready(page, "h1")
        page.click(".dvr .dattr [data-aadd]"); page.fill(".dvr .dva-w", 'style="color: rgb(255, 0, 0)"'); page.press(".dvr .dva-w", "Enter")
        want3 = want2.decode().replace('<h1 id="headline">', '<h1 id="headline" style="color: rgb(255, 0, 0)">').encode()
        file_is(f, want3)
        frame.wait_for_function("() => getComputedStyle(document.getElementById('headline')).color === 'rgb(255, 0, 0)'")
        page.wait_for_selector(".dvr .dattr .dva[data-a=style] .dva-v")
        ready(page, "h1")
        sv = ".dvr .dattr .dva[data-a=style] .dva-v"
        page.fill(sv, "color: rgb(0, 0, 255); letter-spacing: 2px"); page.press(sv, "Enter")
        want4 = want3.decode().replace('style="color: rgb(255, 0, 0)"', 'style="color: rgb(0, 0, 255); letter-spacing: 2px"').encode()
        file_is(f, want4)
        frame.wait_for_function("() => getComputedStyle(document.getElementById('headline')).color === 'rgb(0, 0, 255)'")
        shot(page, "dev-editmode-attrs-dark.png")

        # History: the four writes after «Opened», newest last; the LED is on
        assert history(page) == [["Opened", True], ["Text", True], ["id", True], ["style", True], ["style", True]], history(page)
        assert page.get_attribute(".dvr .ih .dvled", "data-s") == "on"
        assert page.inner_text(".dvr [data-tab=hist] em") == "4"

        # 4. ⌘Z takes them back one by one to the first bytes, the page follows; ⇧⌘Z makes one again
        blur(page)
        for want in (want3, want2, want1, orig):
            page.keyboard.press("Meta+z"); file_is(f, want)
        frame.wait_for_function("() => document.getElementById('title') && document.getElementById('title').textContent === 'Hello world'")
        assert [on for _w, on in history(page)] == [True, False, False, False, False]
        page.keyboard.press("Meta+Shift+z"); file_is(f, want1)
        # a click on History: the file right after that write («style», the last one), then back to the file as it was opened
        page.click(".dvr [data-tab=hist]"); page.click(".dvr .dvhl .dvhr[data-j='3']"); file_is(f, want4)
        page.click(".dvr .dvhl .dvhr[data-j='-1']"); file_is(f, orig)
        frame.wait_for_function("() => document.getElementById('title') && !document.getElementById('title').getAttribute('style')")
        shot(page, "dev-editmode-history-dark.png")
        assert not errors, errors
        br.close()


def test_rename_delete_and_typing_in_the_page(ed):  # noqa: F811
    port, lib, state, tmp = ed
    f = lib / "site/edit.html"; orig = f.read_bytes()
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        page.click(".dvr .hy-bh [data-edit]"); page.wait_for_function("() => __dev.D.edit && __dev.D.picking")
        # the list: an li of it picked in the page, its parent picked from the crumbs
        click_in(page, frame, "#list li:nth-child(2)"); picked(page, "li", "One")
        page.click(".dvr .ih .dvup"); ready(page, "ul")
        assert page.evaluate("__dev.D.detail.d") == "list"

        # 1. the tag renamed in the tree: the start tag and the end tag, nothing else; the page's list keeps its script's item
        page.dblclick(".dvt .row.sel .dtg"); page.wait_for_selector(".dvt .row .dvin")
        page.fill(".dvt .row .dvin", "ol"); page.press(".dvt .row .dvin", "Enter")
        line = '<ul id="list"><li>One</li><li>Two</li></ul>'
        want1 = PAGE.replace(line, '<ol id="list"><li>One</li><li>Two</li></ol>').encode()
        file_is(f, want1)
        frame.wait_for_function("() => { const l = document.getElementById('list'); return l && l.tagName === 'OL' && l.children.length === 3 }")

        # 2. ⌫ in the tree deletes it: its whole line goes from the file, the element from the page
        ready(page, "ol")
        page.focus(".dvt"); page.keyboard.press("Backspace")
        want2 = PAGE.replace(line, '<ol id="list"><li>One</li><li>Two</li></ol>').replace('    <ol id="list"><li>One</li><li>Two</li></ol>\n', "").encode()
        file_is(f, want2)
        frame.wait_for_function("() => !document.getElementById('list')")
        assert [w for w, _on in history(page)] == ["Opened", "Tag", "Deleted"], history(page)

        # 3. ⌘Z: the element back where it stood in the page, then its old tag
        blur(page); page.keyboard.press("Meta+z"); file_is(f, want1)
        frame.wait_for_function("() => { const l = document.getElementById('list'); return l && l.tagName === 'OL' && l.previousElementSibling && l.previousElementSibling.id === 'hero' }")
        page.keyboard.press("Meta+z"); file_is(f, orig)
        frame.wait_for_function("() => document.getElementById('list').tagName === 'UL'")

        # 4. Select off, Edit on: a double click on a text in the page types it; Enter writes it; the tree shows it
        page.keyboard.press("i"); page.wait_for_function("() => __dev.D.edit && !__dev.D.picking")
        box = page.locator(".plg[data-id=e1] iframe.dvf").bounding_box()
        x, y = frame.evaluate("(() => { const r = document.getElementById('lead').getBoundingClientRect(); return [r.left + 10, r.top + r.height / 2] })()")
        s = box["width"] / 1280
        page.mouse.dblclick(box["x"] + x * s, box["y"] + y * s)
        frame.wait_for_function("() => document.getElementById('lead').isContentEditable")
        page.keyboard.type("Typed"); page.keyboard.press("Enter")
        file_is(f, PAGE.replace('<p id="lead">Some text</p>', '<p id="lead">Typed</p>').encode())
        page.wait_for_selector(".dvt .row .dtx:text-is('Typed')", timeout=5000)

        # 5. the script's element: no field, the reason instead, the file as it was
        before = f.read_bytes()
        page.keyboard.press("i"); page.wait_for_function("() => __dev.D.picking")
        click_in(page, frame, "#dyn"); picked(page, "div")
        page.dblclick(".dvt .row.sel .dtg"); page.wait_for_timeout(500)
        assert page.locator(".dvt .row .dvin").count() == 0 and f.read_bytes() == before
        assert page.evaluate("[...document.querySelectorAll('.dvr .dattr')].every(s => s.inert)")
        assert not errors, errors
        br.close()


GEO = """() => { const R = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return { x: r.left, y: r.top, w: r.width, h: r.height, r: r.right, fs: s.fontSize, fw: s.fontWeight, br: s.borderRadius, bg: s.backgroundColor, bt: s.borderTopWidth, bb: s.borderBottomWidth }; };
  const b = document.querySelector('.dvr'), q = s => b.querySelector(s);
  return { blk: R(b), bh: R(q('.hy-bh')), tabs: [...b.querySelectorAll('.hy-bh .hy-bh-tab')].map(R), names: [...b.querySelectorAll('.hy-bh .hy-bh-tab')].map(t => t.textContent.trim()),
    edit: R(q('[data-edit]')), track: (s => ({ w: parseFloat(s.width), h: parseFloat(s.height), bg: s.backgroundColor }))(getComputedStyle(q('[data-edit]'), '::before')),
    ih: R(q('.ih')), tile: R(q('.ih .dvth')), b: R(q('.ih b')), q: R(q('.ih .dvq')), crumb: q('.ih .dvq').textContent,
    led: R(q('.ih .dvled')), sh: R(q('.inf .hy-sh')), fld: R(q('.inf .dnf .dfi')), bl: parseFloat(getComputedStyle(b).borderLeftWidth) }; }"""


def test_the_block_matches_round_15(ed):  # noqa: F811
    port, lib, state, tmp = ed
    with sync_playwright() as p:
        br, page, frame, errors = studio(p, port)
        page.click(".dvr .hy-bh [data-edit]"); page.wait_for_function("() => __dev.D.picking")
        click_in(page, frame, "#title"); picked(page, "h1", "Hello world"); page.wait_for_timeout(300)
        g = page.evaluate(GEO)
        # the header: 34 px, Inspector | History, standard 24 px tabs (12.5 / 500), the first 8 px in from the block's edge, 2 px between
        assert round(g["bh"]["h"]) == 34 and g["names"] == ["Inspector", "History"], g
        assert all(round(t["h"]) == 24 and t["fs"] == "12.5px" and t["fw"] == "500" for t in g["tabs"]), g["tabs"]
        assert round(g["tabs"][0]["x"] - g["blk"]["x"] - g["bl"]) == 8 and round(g["tabs"][1]["x"] - g["tabs"][0]["r"]) == 2, g
        assert g["bh"]["bb"] == "0px" and g["ih"]["bt"] == "0px", "no line where the header meets its content (round 14)"
        # Edit, Hyimg's mini toggle: 22 px (its checkbox 24) at the header's right end, an 11 px track in the studio's green when on
        assert round(g["edit"]["h"]) == 22 and abs(g["edit"]["r"] - (g["blk"]["r"] - g["bl"] - 6)) <= 1, g["edit"]
        assert round(g["track"]["h"]) == 11 and round(g["track"]["w"]) == 20
        green = page.evaluate("() => { const p = document.createElement('i'); p.style.color = '#2fae6a'; document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }")
        assert g["track"]["bg"] == green, g["track"]
        # the picked element: a 46 px row under the header, the 30 px tile, its tag 13 / 600, «parent › itself · W × H» 11.5 under it
        assert round(g["ih"]["h"]) == 46 and round(g["ih"]["y"]) == round(g["bh"]["y"] + g["bh"]["h"]), g["ih"]
        assert [round(g["tile"]["w"]), round(g["tile"]["h"]), g["tile"]["br"]] == [30, 30, "7px"] and round(g["tile"]["x"] - g["blk"]["x"] - g["bl"]) == 14
        assert [g["b"]["fs"], g["b"]["fw"], g["q"]["fs"]] == ["13px", "600", "11.5px"], g
        assert g["crumb"].replace(" ", "").startswith("header#top›h1#title·1280×"), g["crumb"]
        # the LED (Hyimg's <hy-led>): 6 px, idle before a write (a ring); on, in the green, after one
        assert [round(g["led"]["w"]), round(g["led"]["h"])] == [6, 6] and page.get_attribute(".dvr .ih .dvled", "data-s") == "idle"
        assert page.get_attribute(".dvr .ih hy-led.dvled", "state") == "off"
        # sections and fields of the inspector as drawn: 28 px heads, 24 px wells
        assert round(g["sh"]["h"]) == 28 and round(g["fld"]["h"]) == 24, g
        # the block scrolls under its header and the crumbs: both stay where they are
        page.evaluate("() => { const b = document.querySelector('.dvr .inf'); b.scrollTop = b.scrollHeight; }"); page.wait_for_timeout(100)
        g2 = page.evaluate(GEO)
        assert page.evaluate("document.querySelector('.dvr .inf').scrollTop") > 100 and (g2["bh"]["y"], g2["ih"]["y"]) == (g["bh"]["y"], g["ih"]["y"]), (g2["bh"], g2["ih"])
        page.fill(".dvr .dattr .dva[data-a=id] .dva-v", "t2"); page.press(".dvr .dattr .dva[data-a=id] .dva-v", "Enter")
        page.wait_for_function("() => document.querySelector('.dvr .ih .dvled').dataset.s === 'on'", timeout=8000)
        assert page.evaluate("() => getComputedStyle(document.querySelector('.dvr .ih .dvled')).backgroundColor") == green
        shot(page, "dev-r15-block-dark.png")
        assert not errors, errors
        br.close()
