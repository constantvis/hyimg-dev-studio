"""The first screen of an HTML page as a PNG, for the library's grid and the card at rest (server.py preview):
python3 render.py <file:// url> <w> <h> <out.png> [scale]. Chromium from Playwright runs the page's scripts; a page that never settles is
drawn as it stands after 15 s. scale is the device pixel ratio: 2 draws the w × h css px page into a picture twice as wide, as a Retina
screen shows it (owner 2026-10-08: a card zoomed in on the board needs 2200 device px)."""
import sys

from playwright.sync_api import sync_playwright

url, w, h, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
scale = float(sys.argv[5]) if len(sys.argv) > 5 else 1
with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": w, "height": h}, **({"device_scale_factor": scale} if scale != 1 else {}))
        try:
            page.goto(url, wait_until="load", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(400)   # fonts and a first animation frame
        page.screenshot(path=out)
    finally:
        browser.close()
