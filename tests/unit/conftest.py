"""Fast unit tests of Dev studio's Python (server.py, render.py): no Chromium, no Playwright browser, no server, no network.

  python3 -m pytest tests/unit -q

server.py is loaded by file path under a name of its own (as Hyimg's server loads a plugin's "server" module); render.py is run with
runpy and a stand-in playwright package.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for _k in [k for k in os.environ if k.startswith(("HYIMG_", "REVIEW_"))]:
    del os.environ[_k]


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for k in [k for k in os.environ if k.startswith(("HYIMG_", "REVIEW_"))]:
        monkeypatch.delenv(k)
    monkeypatch.delitem(sys.modules, "config", raising=False)


@pytest.fixture
def server():
    spec = importlib.util.spec_from_file_location("hyimg_plugin_dev_unit", ROOT / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
