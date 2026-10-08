"""render.py: the first screen of an HTML page as a PNG (python3 render.py <file:// url> <w> <h> <out.png>). It runs here with a stand-in
playwright package, so what it asks of Chromium (viewport, how long to wait, where the picture goes, that the browser is always closed)
is checked without a browser."""
import runpy
import sys
import types
from pathlib import Path

import pytest

RENDER = str(Path(__file__).resolve().parents[2] / "render.py")


class Browser:
    def __init__(self, log, goto_error=None, shot_error=None):
        self.log, self.goto_error, self.shot_error = log, goto_error, shot_error

    def new_page(self, viewport=None, **kw):
        self.log.append(("new_page", viewport, *([kw] if kw else [])))
        return Page(self)

    def close(self):
        self.log.append(("close",))


class Page:
    def __init__(self, browser):
        self.b = browser

    def goto(self, url, wait_until=None, timeout=None):
        self.b.log.append(("goto", url, wait_until, timeout))
        if self.b.goto_error:
            raise self.b.goto_error

    def wait_for_timeout(self, ms):
        self.b.log.append(("wait", ms))   # no real wait

    def screenshot(self, path=None):
        self.b.log.append(("screenshot", path))
        if self.b.shot_error:
            raise self.b.shot_error
        Path(path).write_bytes(b"\x89PNG")


@pytest.fixture
def render(monkeypatch):
    def run(*argv, goto_error=None, shot_error=None):
        log = []

        class Playwright:
            chromium = types.SimpleNamespace(launch=lambda: log.append(("launch",)) or Browser(log, goto_error, shot_error))

        class Ctx:
            def __enter__(self):
                return Playwright()

            def __exit__(self, *exc):
                log.append(("stop",))
                return False

        pkg = types.ModuleType("playwright")
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = Ctx
        monkeypatch.setitem(sys.modules, "playwright", pkg)
        monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
        monkeypatch.setattr(sys, "argv", ["render.py", *argv])
        try:
            runpy.run_path(RENDER, run_name="__main__")
        finally:
            run.log = log
        return log
    return run


def test_the_page_is_opened_at_the_asked_size_and_its_first_screen_saved(render, tmp_path):
    out = tmp_path / "k.png"
    log = render("file:///lib/site/index.html", "1280", "800", str(out))
    assert log == [("launch",), ("new_page", {"width": 1280, "height": 800}), ("goto", "file:///lib/site/index.html", "load", 15000),
                   ("wait", 400), ("screenshot", str(out)), ("close",), ("stop",)]
    assert out.read_bytes() == b"\x89PNG"


def test_scale_2_draws_the_page_at_its_css_size_into_twice_the_pixels(render, tmp_path):
    log = render("file:///lib/site/index.html", "1280", "800", str(tmp_path / "k.png"), "2")
    assert log[1] == ("new_page", {"width": 1280, "height": 800}, {"device_scale_factor": 2.0})


def test_a_page_that_never_finishes_loading_is_drawn_as_it_stands(render, tmp_path):
    out = tmp_path / "k.png"
    log = render("file:///slow.html", "640", "480", str(out), goto_error=TimeoutError("Timeout 15000ms exceeded"))
    assert ("screenshot", str(out)) in log and out.exists()


def test_the_browser_is_closed_even_when_the_picture_cannot_be_taken(render, tmp_path):
    with pytest.raises(RuntimeError):
        render("file:///a.html", "640", "480", str(tmp_path / "k.png"), shot_error=RuntimeError("Target closed"))
    assert render.log[-2:] == [("close",), ("stop",)]


@pytest.mark.parametrize("argv, error", [(("file:///a.html", "wide", "800", "out.png"), ValueError), (("file:///a.html", "1280"), IndexError), ((), IndexError)])
def test_bad_arguments_stop_it_before_a_browser_starts(render, argv, error):
    with pytest.raises(error):
        render(*argv)
    assert render.log == []
