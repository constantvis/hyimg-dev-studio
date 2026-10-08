"""Fast unit tests of Dev studio's Python (server.py, render.py): no Chromium, no Playwright browser, no server, no network.

  python3 -m pytest tests/unit -q

server.py is loaded by file path under a name of its own (as Hyimg's server loads a plugin's "server" module); render.py is run with
runpy and a stand-in playwright package.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The core's guard (hyimg/tests/procguard.py) also when pytest runs tests/unit alone, which does not load tests/conftest.py: the
# session's own cache folder, and the check of the person's ~/Library/Caches/Hyimg when the session ends
_GUARD = Path(os.environ.get("HYIMG_REPO") or ROOT.parent / "hyimg") / "tests" / "procguard.py"
procguard = sys.modules.get("procguard")
if procguard is None and _GUARD.is_file():
    _spec = importlib.util.spec_from_file_location("procguard", _GUARD)
    procguard = sys.modules["procguard"] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(procguard)
if procguard:
    procguard.install()
CACHE = procguard.CACHE if procguard else tempfile.mkdtemp(prefix="hyimg-test-cache-")

for _k in [k for k in os.environ if k.startswith(("HYIMG_", "REVIEW_"))]:
    del os.environ[_k]
os.environ["HYIMG_CACHE_ROOT"] = CACHE   # cleared with the rest and put back: nothing falls back to ~/Library/Caches/Hyimg


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for k in [k for k in os.environ if k.startswith(("HYIMG_", "REVIEW_"))]:
        monkeypatch.delenv(k)
    monkeypatch.setenv("HYIMG_CACHE_ROOT", CACHE)
    monkeypatch.delitem(sys.modules, "config", raising=False)


@pytest.fixture
def server():
    spec = importlib.util.spec_from_file_location("hyimg_plugin_dev_unit", ROOT / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pytest_sessionfinish(session, exitstatus):   # once a session, with tests/conftest.py or without it
    if procguard:
        procguard.finish(session)
