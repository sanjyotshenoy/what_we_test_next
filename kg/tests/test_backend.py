import os
import subprocess
import sys

import pytest

from kg.backend import mode, wants_gpu


@pytest.mark.parametrize("value, expected", [
    (None, False), ("", False), ("0", False), ("false", False), ("no", False),
    ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("gpu", True),
])
def test_wants_gpu(value, expected):
    env = {} if value is None else {"WWTN_GPU": value}
    assert wants_gpu(env) is expected


def test_default_mode_is_cpu():
    assert mode() == "cpu"


def test_gpu_requested_after_pandas_import_fails_loudly():
    """GPU mode must be chosen before pandas is imported, or it would silently run on the CPU."""
    code = "import pandas, os; os.environ['WWTN_GPU'] = '1'; import kg"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={**os.environ, "WWTN_GPU": ""})
    assert result.returncode != 0
    assert "before pandas" in result.stderr
