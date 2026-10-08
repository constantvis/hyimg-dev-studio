"""server.py: Dev studio's POST routes are the edits of 0.2 (source, edit, undo; tests/unit/test_htmledit.py) and it draws an HTML file's
picture by running render.py in a process of its own (preview(full, out_png), owner 2026-10-06). subprocess.run is a stand-in: no process
is started."""
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runs(server, monkeypatch):
    seen = []

    def run(args, **kw):
        seen.append({"args": args, "kw": kw})
        return subprocess.CompletedProcess(args, 0, b"", b"")
    monkeypatch.setattr(server, "subprocess", types.SimpleNamespace(run=run))
    return seen


def test_dev_studio_routes_are_the_edits_only(server):
    assert sorted(server.ROUTES) == ["edit", "source", "undo"]


def test_the_manifest_gives_html_files_to_this_server_module():
    man = json.loads((ROOT / "manifest.json").read_text())
    assert man["server"] == "server.py" and man["kinds"] == {"html": [".html", ".htm"]}


def test_a_page_is_drawn_by_render_py_at_1280_by_800_twice_as_sharp_with_this_python(server, runs, tmp_path):
    page = tmp_path / "site" / "index.html"
    server.preview(str(page), str(tmp_path / "k.png"))
    # scale 2: a 2560 × 1600 picture, for a card zoomed in on a Retina screen (2026-10-08)
    assert runs[0]["args"] == [sys.executable, str(ROOT / "render.py"), page.as_uri(), "1280", "800", str(tmp_path / "k.png"), "2"]
    assert runs[0]["kw"] == {"capture_output": True, "timeout": 60}
    assert server.PREVIEW_KEY == "2x"   # Hyimg names these pictures apart from the 1280 ones drawn before, so those are drawn again


def test_a_card_of_its_own_viewport_is_drawn_at_it(server, runs, tmp_path):
    page = tmp_path / "site" / "index.html"
    server.preview_at(str(page), str(tmp_path / "k.png"), 1440, 900)   # a 1440 card: its live page's layout, at twice the size
    assert runs[0]["args"][3:] == ["1440", "900", str(tmp_path / "k.png"), "2"]


def test_a_path_with_spaces_and_cyrillic_becomes_a_well_formed_file_url(server, runs, tmp_path):
    server.preview(str(tmp_path / "Мой сайт" / "a#b.html"), str(tmp_path / "k.png"))
    url = runs[0]["args"][2]
    assert url.startswith("file:///") and " " not in url and "#" not in url and "%D0%9C" in url


def test_a_relative_path_is_refused_before_any_process_starts(server, runs):
    with pytest.raises(ValueError):
        server.preview("site/index.html", "never.png")
    assert runs == []


def test_a_page_that_never_settles_lets_the_timeout_through_so_hyimg_falls_back_to_quick_look(server, monkeypatch, tmp_path):
    def run(args, **kw):
        raise subprocess.TimeoutExpired(args, kw["timeout"])
    monkeypatch.setattr(server, "subprocess", types.SimpleNamespace(run=run))
    with pytest.raises(subprocess.TimeoutExpired):
        server.preview(str(tmp_path / "a.html"), str(tmp_path / "k.png"))


def test_a_render_that_fails_raises_nothing_and_leaves_no_picture(server, monkeypatch, tmp_path):
    monkeypatch.setattr(server, "subprocess", types.SimpleNamespace(run=lambda args, **kw: subprocess.CompletedProcess(args, 1, b"", b"Traceback")))
    assert server.preview(str(tmp_path / "a.html"), str(tmp_path / "k.png")) is None
    assert not (tmp_path / "k.png").exists()
