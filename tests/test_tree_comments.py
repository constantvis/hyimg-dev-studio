"""A comment from Dev Studio's element tree (owner 2026-10-08: «в дереве слева я могу выбрать именно нужный элемент ... А что если в дереве я
точно так же смогу нажать и оставить комментарий? Оно у меня покажется уже на канвасе»). On a disposable library, Chromium, the dark theme:

- the comment button on a row (hover), «Comment» in the row's right-click menu and C with the tree focused each open the board's composer
  on that row's element; the thread carries the element's selector, row path and text, its point lies inside the element's box on the
  card, and hy.py comments names the element
- an element too small to hit, one under another, one in a scroller out of sight (scrolled into it) and one with display: contents (its
  contents' box, pin "kids") all get their pin on them
- a row with a thread shows its count, a click on it opens the thread, and under the pointer a «+» for another thread; a row under the
  pointer lights its pins on the board; a pin opened on the board selects its row; an @mention reaches the agent as with any comment
- a row flush with its list's bottom edge and a slide flush with its slider's right edge are out of sight: they scroll in; Esc on the box
  gives the slider its scroll back; a slide scrolled out of its slider has no pin over the page; a tall element whose top is scrolled
  above the viewport keeps its pin after Send, and hy.py says it is further down than the card's picture
- Esc out of Dev Studio with the pointer on a row with a thread leaves no pin lit; after Done the pin stands on the card's still

  HYIMG_REPO=<Hyimg checkout> python3 -m pytest tests/test_tree_comments.py      HYIMG_SHOTS=<folder> saves the screenshots
"""
import json, os, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from test_dev_studio import REPO, HERE, free_port

SHOTS = os.environ.get("HYIMG_SHOTS")
ME = str(uuid.uuid4())
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Tree comments</title><style>
body{margin:0;font:16px system-ui;background:#0b7a5a;color:#fff} #t{font-size:48px;margin:24px}
#dot{display:inline-block;width:3px;height:3px;background:#f33;margin-left:300px} .wrap{display:contents}
#box{height:120px;width:400px;overflow:auto;margin:24px;background:#035} #box .pad{height:600px}
#lid{position:relative;margin-top:-34px;height:44px;width:200px;background:#333}
#list{list-style:none;margin:8px 24px;padding:0;height:100px;width:300px;overflow:auto;background:#035} #list li{height:20px;line-height:20px}
#car{display:flex;width:300px;overflow:hidden;margin:8px 24px;background:#530} #car .sl{flex:0 0 300px;height:40px} #s{height:2400px;margin:24px;background:#063}
</style></head><body><header id="top"><h1 id="t">Hello</h1></header>
<main><span id="dot"></span><div class="wrap" id="wrap"><button id="b1">One</button> <button id="b2">Two</button></div>
<div id="box"><div class="pad"></div><p id="deep">Deep inside</p></div><button id="cover">Under the lid</button><div id="lid"></div></main>
<ul id="list"><li>Row 1</li><li>Row 2</li><li>Row 3</li><li>Row 4</li><li>Row 5</li><li>Row 6</li><li>Row 7</li><li>Row 8</li></ul>
<div id="car"><div class="sl" id="s1">Slide one</div><div class="sl" id="s2">Slide two</div></div><section id="s">Tall section</section>
</body></html>"""
KEY = {"t": "html>body:1>header:0>h1:0", "main": "html>body:1>main:1", "dot": "html>body:1>main:1>span:0", "wrap": "html>body:1>main:1>div:1",
       "box": "html>body:1>main:1>div:2", "deep": "html>body:1>main:1>div:2>p:1", "cover": "html>body:1>main:1>button:3",
       "list": "html>body:1>ul:2", "li6": "html>body:1>ul:2>li:5", "car": "html>body:1>div:3", "s2": "html>body:1>div:3>div:1", "s": "html>body:1>section:4"}
ROW = lambda k: f'.dvt .row[data-p="{KEY[k]}"]'


@pytest.fixture
def hy(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"cv.lang": "en", "cv.theme": "dark"}))
    (tmp_path / "profile.json").write_text(json.dumps({"id": ME, "name": "Ann Lee", "color": "green", "created": ""}))
    lib, state, plugins = tmp_path / "lib", tmp_path / "state", tmp_path / "plugins"
    for p in (lib / "site", state / "boards", plugins): p.mkdir(parents=True)
    (lib / "site/index.html").write_text(PAGE)
    (plugins / "dev").symlink_to(HERE)
    items = {"h1": {"type": "html", "src": "site/index.html", "vw": 1280, "x": 0, "y": 0, "w": 640, "h": 400, "pics": ["site/index.html"]}}
    (state / "boards/main.json").write_text(json.dumps({"schema": 1, "revision": 1, "items": items, "groups": {}, "removed": {}}))
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HYIMG_", "REVIEW_"))}
    (tmp_path / "home").mkdir()
    env.update(HOME=str(tmp_path / "home"), PLAYWRIGHT_BROWSERS_PATH=os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(Path.home() / "Library/Caches/ms-playwright"))
    env.update(HYIMG_LIBRARY_ROOT=str(lib), HYIMG_STATE_ROOT=str(state), HYIMG_PROJECT_ID=str(uuid.uuid4()), HYIMG_PLUGINS=str(plugins),
               HYIMG_SETTINGS=str(tmp_path / "settings.json"), PYTHONDONTWRITEBYTECODE="1", HY_TEST_ONLY_PLUGINS="1")
    log = open(tmp_path / "server.log", "w+")
    proc = subprocess.Popen([sys.executable, str(REPO / "review/server.py"), str(port)], env=env, stdout=log, stderr=log)
    for _ in range(100):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); break
        except OSError: time.sleep(0.1)
    try:
        yield port
    finally:
        proc.terminate(); proc.wait(5); log.close()


def threads(port):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/comments?name=main", timeout=10))["items"]


def wait(fn, what, t=10):
    end = time.time() + t
    while time.time() < end:
        v = fn()
        if v: return v
        time.sleep(0.1)
    raise AssertionError(what)


def shot(page, name):
    if SHOTS: os.makedirs(SHOTS, exist_ok=True); page.screenshot(path=os.path.join(SHOTS, name))


def rect(page, css):
    """an element's box in the page's viewport (css px)"""
    return page.frame_locator(".plg[data-id=h1] iframe.dvf").locator(css).evaluate(
        "el => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")


def write(page, port, text):
    """the composer is open: type, send; the thread as the server keeps it"""
    page.wait_for_selector("#cmthread.open[data-c=draft] textarea")
    page.keyboard.type(text); page.keyboard.press("Enter")
    page.wait_for_selector("#cmthread.open:not([data-c=draft])")
    return wait(lambda: next((t for t in threads(port) if t["messages"][0]["text"].endswith(text)), None), f"no thread «{text}»")


def inside(t, r, pad=0.6):
    """the thread's point (shares of the card, page px at 1280 × 800) lies in the box r = [x, y, w, h] in page px"""
    x, y = t["at"][0] * 1280, t["at"][1] * 800
    return r[0] - pad <= x <= r[0] + r[2] + pad and r[1] - pad <= y <= r[1] + r[3] + pad, (x, y, r)


def pin_on(page, tid, r):
    """the pin's point on screen (its bottom left corner) lies on the element's box in the live page"""
    fb = page.locator(".plg[data-id=h1] iframe.dvf").bounding_box(); s = fb["width"] / 1280
    p = page.locator(f'#cmpins [data-c="{tid}"]').bounding_box()
    x, y = p["x"], p["y"] + p["height"]
    return fb["x"] + r[0] * s - 1.5 <= x <= fb["x"] + (r[0] + r[2]) * s + 1.5 and fb["y"] + r[1] * s - 1.5 <= y <= fb["y"] + (r[1] + r[3]) * s + 1.5, (x, y, r)


def unfold(page, k):
    page.locator(f"{ROW(k)} .chev").click(); page.wait_for_selector(f'{ROW(k)}[aria-expanded="true"]')


def test_a_comment_from_the_tree_lands_on_the_element(hy):
    port = hy
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={"width": 1600, "height": 960}, color_scheme="dark")
        errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.evaluate("() => { localStorage.setItem('cv.nolib', '1'); localStorage.setItem('cv.lod', '0'); }")
        page.goto(f"http://127.0.0.1:{port}/canvas.html")
        page.wait_for_function("() => typeof PLGST !== 'undefined' && PLGST.some(x => x.name === 'dev' && x.ok) && window.hyAnnot && window.hyComments"
                               " && window.hyPeople && hyPeople.me()", timeout=30000)
        page.evaluate("() => __dev.openDev('h1')")
        page.wait_for_function("() => __dev.D && __dev.D.tree && __dev.D.tree.root", timeout=20000)
        page.wait_for_timeout(800)   # the camera's flight and the library folding
        page.wait_for_selector('.dvt .row[data-p="html>body:1>header:0"]')
        page.locator('.dvt .row[data-p="html>body:1>header:0"] .chev').click(); page.wait_for_selector(ROW("t"))

        # 1. the button on the row under the pointer: the board's composer on the element, an @mention of the agent
        page.hover(ROW("t")); page.wait_for_selector(f"{ROW('t')} hy-icon-button.dvcb button")
        shot(page, "1-row-button.png")
        page.click(f"{ROW('t')} .dvcb")
        page.wait_for_selector("#cmthread.open[data-c=draft] textarea")
        assert page.locator("#cmthread .cm-h .cm-w").inner_text().strip() == "· #t"
        assert page.evaluate("() => __dev.D.sel") == page.locator(ROW("t")).evaluate("r => +r.dataset.i")
        page.keyboard.type("@Clau"); page.wait_for_selector("#cmat [data-cm=pick]"); page.keyboard.press("Enter")
        shot(page, "2-composer-from-tree.png")
        t1 = write(page, port, " make the heading bigger")
        assert t1["anchor"]["obj"] == "h1" and t1["anchor"]["kind"] == "html" and t1["anchor"]["file"] == "site/index.html"
        assert t1["element"]["css"] == "#t" and t1["element"]["key"] == KEY["t"] and t1["element"]["tag"] == "h1" and t1["element"]["text"] == "Hello"
        assert "pin" not in t1["element"] and t1["messages"][0]["mentions"][0]["agent"] == "claude"
        r = rect(page, "#t"); assert inside(t1, r)[0], inside(t1, r)
        page.wait_for_selector(f'#cmpins [data-c="{t1["id"]}"]'); assert pin_on(page, t1["id"], r)[0], pin_on(page, t1["id"], r)
        # the row shows its count, and the thread's pin stood on the element as a click there would have put it
        page.wait_for_selector(f"{ROW('t')} .dvcn"); assert page.locator(f"{ROW('t')} .dvcn").inner_text().strip() == "1"
        page.keyboard.press("Escape"); page.mouse.move(5, 500); page.wait_for_timeout(200)
        shot(page, "3-row-count.png")

        # 2. the menu, on an element 3 × 3 px
        unfold(page, "main")
        page.click(ROW("dot"), button="right"); page.wait_for_selector('#ctx.open [data-act="comment"]')
        page.click('#ctx.open [data-act="comment"]')
        t2 = write(page, port, "This dot is too small to click")
        assert t2["element"]["css"] == "#dot" and t2["element"]["key"] == KEY["dot"] and "pin" not in t2["element"]
        r = rect(page, "#dot"); assert r[2] == 3 and inside(t2, r)[0], inside(t2, r)
        page.keyboard.press("Escape")

        # 3. C with the tree focused: an element out of sight in a scroller is scrolled into it
        unfold(page, "box")
        assert rect(page, "#deep")[1] > 400   # under the scroller's bottom (its top is about 150)
        page.click(ROW("deep")); page.keyboard.press("c")
        t3 = write(page, port, "Deep paragraph")
        assert t3["element"]["css"] == "#deep" and t3["element"]["key"] == KEY["deep"] and "pin" not in t3["element"]
        r = rect(page, "#deep"); box_r = rect(page, "#box")
        assert box_r[1] <= r[1] and r[1] + r[3] <= box_r[1] + box_r[3] + .5, (r, box_r)   # in sight now
        assert inside(t3, r)[0], inside(t3, r)
        page.keyboard.press("Escape")

        # 4. display: contents draws no box: the pin on its contents; a button under another element still gets its pin on it
        page.hover(ROW("wrap")); page.click(f"{ROW('wrap')} .dvcb")
        t4 = write(page, port, "These two buttons")
        assert t4["element"]["css"] == "#wrap" and t4["element"].get("pin") == "kids"
        b1, b2 = rect(page, "#b1"), rect(page, "#b2")
        assert inside(t4, [b1[0], min(b1[1], b2[1]), b2[0] + b2[2] - b1[0], max(b1[3], b2[3])])[0]
        page.keyboard.press("Escape")
        page.hover(ROW("cover")); page.click(f"{ROW('cover')} .dvcb")
        t5 = write(page, port, "The lid hides this button")
        assert t5["element"]["css"] == "#cover" and inside(t5, rect(page, "#cover"))[0]
        page.keyboard.press("Escape")

        # 5. a row under the pointer lights its pins; its count opens the thread; a pin opened on the board selects its row
        page.hover(ROW("t"))
        assert "lit" in page.locator(f'#cmpins [data-c="{t1["id"]}"]').get_attribute("class")
        page.wait_for_timeout(300); shot(page, "5-row-hover-lights-pin.png")   # the ring's easing
        assert "lit" not in page.locator(f'#cmpins [data-c="{t2["id"]}"]').get_attribute("class")
        # the row with a thread: under the pointer a «+» before its count, another thread on the same element
        assert page.locator(f"{ROW('t')} .dvcb").get_attribute("icon") == "plus" and page.locator(f"{ROW('t')} .dvcb + .dvcn").count() == 1
        page.click(f"{ROW('t')} .dvcb"); page.wait_for_selector("#cmthread.open[data-c=draft] textarea")
        assert page.locator("#cmthread .cm-h .cm-w").inner_text().strip() == "· #t"
        page.keyboard.press("Escape"); page.wait_for_selector("#cmthread.open", state="detached")
        page.click(f"{ROW('t')} .dvcn"); page.wait_for_selector(f'#cmthread.open[data-c="{t1["id"]}"]')
        page.keyboard.press("Escape"); page.mouse.move(5, 500)
        assert "lit" not in page.locator(f'#cmpins [data-c="{t1["id"]}"]').get_attribute("class")
        page.click(ROW("main")); page.locator('.dvt .row[data-p="html>body:1>header:0"] .chev').click()   # another row, the heading's folded away
        page.wait_for_selector(ROW("t"), state="detached")
        page.wait_for_selector('.dvt .row[data-p="html>body:1>header:0"] hy-badge.dvcd[dot]')   # folded, with a thread inside
        page.locator(f'#cmpins [data-c="{t1["id"]}"]').click()
        page.wait_for_selector(f'#cmthread.open[data-c="{t1["id"]}"]')
        page.wait_for_selector(f"{ROW('t')}.sel")
        assert page.evaluate("() => __dev.D.sel") == page.locator(ROW("t")).evaluate("r => +r.dataset.i")
        page.keyboard.press("Escape")

        # 5b. a row flush with its list's bottom edge is out of sight: the list scrolls, the pin stands on the row, not on the list's border
        js = lambda f: page.frame_locator(".plg[data-id=h1] iframe.dvf").locator("body").evaluate(f)
        unfold(page, "list"); page.click(ROW("li6")); page.keyboard.press("c")
        page.wait_for_selector("#cmthread.open[data-c=draft] textarea")
        assert js("() => document.getElementById('list').scrollTop") > 0
        t6 = write(page, port, "Sixth row")
        r, lr = rect(page, "#list > li:nth-of-type(6)"), rect(page, "#list")
        assert t6["element"]["css"] == "#list > li:nth-of-type(6)" and "pin" not in t6["element"] and inside(t6, r)[0], inside(t6, r)
        assert t6["at"][1] * 800 < lr[1] + lr[3] - 4, (t6["at"], lr)   # off the list's bottom border
        wait(lambda: pin_on(page, t6["id"], r)[0], f"the pin is not on the row: {pin_on(page, t6['id'], r)}")
        shot(page, "6-flush-row.png")
        page.keyboard.press("Escape")

        # 5c. a slide flush with its slider's right edge: the slider scrolls to it while the box is open, Esc gives the scroll back (nobody can
        # scroll an overflow: hidden box by hand); sent, the pin stands on the slide and goes when the slide is scrolled out of the slider
        unfold(page, "car"); page.hover(ROW("s2")); page.click(f"{ROW('s2')} .dvcb")
        page.wait_for_selector("#cmthread.open[data-c=draft] textarea")
        assert js("() => document.getElementById('car').scrollLeft") == 300
        shot(page, "7-slide-composer.png")
        page.keyboard.press("Escape")
        wait(lambda: js("() => document.getElementById('car').scrollLeft") == 0, "Esc did not give the slider its scroll back")
        page.hover(ROW("s2")); page.click(f"{ROW('s2')} .dvcb"); t7 = write(page, port, "Second slide")
        r = rect(page, "#s2"); assert "pin" not in t7["element"] and inside(t7, r)[0], inside(t7, r)
        wait(lambda: pin_on(page, t7["id"], r)[0], f"the pin is not on the slide: {pin_on(page, t7['id'], r)}")
        page.keyboard.press("Escape")
        js("() => { document.getElementById('car').scrollLeft = 0; }")
        page.wait_for_selector(f'#cmpins [data-c="{t7["id"]}"]', state="detached")   # no pin floating beside the slider
        shot(page, "8-slide-scrolled-away.png")

        # 5d. a tall element whose top is scrolled 600 px above the viewport: the pin stands on the part one sees, after Send too
        js("() => scrollTo(0, document.getElementById('s').offsetTop + 600)")
        page.hover(ROW("s")); page.click(f"{ROW('s')} .dvcb"); t8 = write(page, port, "Tall section")
        r = rect(page, "#s"); seen = [r[0], max(r[1], 0), r[2], min(r[1] + r[3], 800) - max(r[1], 0)]
        assert r[1] < -500 and t8["at"][1] == 0.98 and t8["element"]["page"][1] > 1000, (r, t8)
        wait(lambda: page.locator(f'#cmpins [data-c="{t8["id"]}"]').count() and pin_on(page, t8["id"], seen)[0], "no pin on the tall element after Send")
        shot(page, "9-tall-scrolled.png")
        page.keyboard.press("Escape"); js("() => scrollTo(0, 0)")

        # 6. agents read it: the element named, the mention of Claude is a task
        env = {k: v for k, v in os.environ.items() if not k.startswith("HYIMG_")} | {"HYIMG_PORT": str(port), "PYTHONDONTWRITEBYTECODE": "1"}
        out = subprocess.run([sys.executable, str(REPO / "review/hy.py"), "comments", "--page", "main"], env=env, capture_output=True, text=True, timeout=60)
        assert out.returncode == 0 and "элемент #t" in out.stdout and "элемент #dot" in out.stdout and "булавка на его содержимом" in out.stdout, out.stdout + out.stderr
        tall = next(x for x in out.stdout.splitlines() if "элемент #s «" in x)   # its own point, past the card's picture
        assert f"({round(t8['element']['page'][0])}, {round(t8['element']['page'][1])} css px страницы, ниже первого экрана" in tall, tall
        out = subprocess.run([sys.executable, str(REPO / "review/hy.py"), "comments", "--page", "main", "--mentions", "claude"], env=env,
                             capture_output=True, text=True, timeout=60)
        assert out.returncode == 0 and "make the heading bigger" in out.stdout and "Deep paragraph" not in out.stdout, out.stdout + out.stderr

        # 7. Esc out of Dev Studio with the pointer on a row with a thread: no pin stays lit; the pin on the card's still, in the element's box
        page.hover(ROW("t")); assert "lit" in page.locator(f'#cmpins [data-c="{t1["id"]}"]').get_attribute("class")
        for _ in range(4):
            if not page.evaluate("() => !!__dev.D"): break
            page.keyboard.press("Escape"); page.wait_for_timeout(150)
        page.wait_for_function("() => !__dev.D"); page.mouse.move(5, 500); page.wait_for_timeout(700)
        assert page.locator("#cmpins .cmpin.lit").count() == 0 and page.evaluate("() => hyComments.state.lit.size") == 0
        cb, pin = page.locator(".plg[data-id=h1]").bounding_box(), page.locator(f'#cmpins [data-c="{t1["id"]}"]').bounding_box()
        assert abs(pin["x"] - (cb["x"] + t1["at"][0] * cb["width"])) < 2 and abs(pin["y"] + pin["height"] - (cb["y"] + t1["at"][1] * cb["height"])) < 3
        shot(page, "4-board-pin.png")
        # the tall section's pin waits at the bottom edge of the card's picture, and says the element is further down
        far = page.locator(f'#cmpins [data-c="{t8["id"]}"]')
        assert far.get_attribute("title").endswith("· further down the page") and abs(far.bounding_box()["y"] + far.bounding_box()["height"] - (cb["y"] + .98 * cb["height"])) < 3
        assert "further" not in page.locator(f'#cmpins [data-c="{t1["id"]}"]').get_attribute("title")
        assert not errors, errors
        br.close()
