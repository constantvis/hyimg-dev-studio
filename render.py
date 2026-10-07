"""The first screen of an HTML page as a PNG, for the library's grid and the card at rest (server.py preview):
python3 render.py <file:// url> <w> <h> <out.png>. Chromium from Playwright runs the page's scripts; a page that never settles is drawn
as it stands after 15 s."""
import sys

from playwright.sync_api import sync_playwright

url, w, h, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": w, "height": h})
        try:
            page.goto(url, wait_until="load", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(400)   # fonts and a first animation frame
        page.screenshot(path=out)
    finally:
        browser.close()
