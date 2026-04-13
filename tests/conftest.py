"""Pytest configuration — isolates the app under test to a temp config dir."""

import os
import tempfile
from pathlib import Path

# Must be set BEFORE any sapa.* import so Config picks it up.
_tmp = tempfile.mkdtemp(prefix="sapa-test-")
os.environ["SAPA_CONFIG_DIR"] = _tmp

import pytest
from fastapi.testclient import TestClient

from sapa.config import reset_config
from sapa.app import app


@pytest.fixture(scope="session")
def client():
    reset_config()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def tmp_config_dir() -> Path:
    return Path(_tmp)
