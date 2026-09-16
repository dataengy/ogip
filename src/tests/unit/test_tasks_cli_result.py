"""The CLI result contract (plan-2 decision 6): non-None return -> one JSON line on stdout."""

import json

import pytest

from ogip.tasks import TASKS, odos_task
from ogip.tasks.__main__ import main


@pytest.fixture(autouse=True)
def _restore_registry():
    """Restore the TASKS registry after each test to avoid polluting other tests."""
    saved = dict(TASKS)
    yield
    TASKS.clear()
    TASKS.update(saved)


def test_string_result_is_printed_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    @odos_task("probe.token")
    def _token() -> str:
        return "12345"

    assert main(["probe.token"]) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert json.loads(lines[-1]) == "12345"


def test_dict_result_round_trips(capsys: pytest.CaptureFixture[str]) -> None:
    @odos_task("probe.check")
    def _check() -> dict[str, object]:
        return {"passed": True, "rows": 7}

    assert main(["probe.check"]) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert json.loads(lines[-1]) == {"passed": True, "rows": 7}


def test_none_result_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    @odos_task("probe.silent")
    def _silent() -> None:
        return None

    assert main(["probe.silent"]) == 0
    assert capsys.readouterr().out.strip() == ""
