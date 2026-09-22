import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
os.environ["ABHAYA_DATA_DIR"] = str(FIXTURES_DIR)
_TEST_DB_PATH = BACKEND_DIR / "tests" / "_test_abhaya.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()
os.environ["ABHAYA_DB_URL"] = f"sqlite:///{_TEST_DB_PATH}"

import pytest


@pytest.fixture(scope="session", autouse=True)
def _reload_graph_once():
    from app.graph import reload_road_graph
    reload_road_graph()
    yield
