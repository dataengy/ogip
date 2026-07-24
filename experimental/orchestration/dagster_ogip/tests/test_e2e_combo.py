"""E2E wrapper — runs the dagster-dlt-dbt combo (source → FS layer) via the shell script.

The canonical e2e is `e2e/run_combo.sh` (also what CI runs); this lets `pytest -m e2e` drive it.
"""

import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "e2e" / "run_combo.sh"


@pytest.mark.e2e
def test_dagster_dlt_dbt_combo_source_to_fs_layer() -> None:
    subprocess.run(["bash", str(_SCRIPT)], check=True)
