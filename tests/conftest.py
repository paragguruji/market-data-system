import logging
import os
import sys
from io import StringIO

import pytest

from src.common.logging_adapter import KeyValContextLogger

sys.path.insert(0, os.path.abspath('src'))


# Need the above line because `Run` command (python3 src/app.py data/config.json) treats "src" as source root dir,
# But `Test` command (python3 -m pytest -p no:warnings) treats parent of src as root dir.
# I'd preferably solve this by adding src/ to PYTHONPATH, or changing run command to python3 -m src.app data/config.json


@pytest.fixture
def log_stream():
    return StringIO("")


@pytest.fixture
def string_logger(log_stream):
    formatter = logging.Formatter("level=%(levelname)s logger=%(name)s %(message)s")
    handler = logging.StreamHandler(stream=log_stream)
    handler.setLevel("DEBUG")
    handler.setFormatter(formatter)
    a_logger = logging.getLogger("string_logger")
    a_logger.propagate = False
    a_logger.setLevel("DEBUG")
    a_logger.addHandler(handler)
    return KeyValContextLogger(logger=a_logger)
