from __future__ import annotations

import os
from pathlib import Path

import pytest

#: The D.24A archive, as UNECE publishes it, from wherever the tester keeps their copy. The repository carries none.
DIRECTORY = os.environ.get("SDC_EDIFACT_DIRECTORY")
HAVE_DIRECTORY = bool(DIRECTORY) and Path(DIRECTORY).is_file()


def pytest_configure(config):
    config.addinivalue_line("markers", "no_directory: runs without the UN/EDIFACT directory")


def pytest_collection_modifyitems(config, items):
    if HAVE_DIRECTORY:
        return
    skip = pytest.mark.skip(reason="set SDC_EDIFACT_DIRECTORY to the D.24A archive downloaded from UNECE")
    for item in items:
        if "no_directory" not in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def _cache(tmp_path_factory):
    os.environ.setdefault("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache")))
