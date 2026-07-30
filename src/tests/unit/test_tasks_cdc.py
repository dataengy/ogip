"""`cdc.catchup` argv construction.

The bash lane once forwarded `"${@:2}"` straight to `cdc/ingestr_cdc.sh`, so both `--dry-run`
and `--stream` reached it. Collapsing that into a typed task is exactly where a flag goes
missing silently, so both are pinned here — as is the refusal to accept both at once.
"""

from pathlib import Path
from unittest import mock

import pytest

from ogip.tasks.cdc import cdc_catchup


def _argv(**kwargs: bool) -> list[str]:
    """Run the task with subprocess stubbed; return the argv it would have executed."""
    with mock.patch("ogip.tasks.cdc.subprocess.run") as run:
        cdc_catchup(**kwargs)
    return list(run.call_args.args[0])


def test_no_flags_runs_the_plain_catchup():
    argv = _argv()
    assert argv[0] == "bash"
    assert argv[1].endswith("ingestr_cdc.sh")
    assert len(argv) == 2


def test_dry_run_forwards_the_dry_run_flag():
    assert _argv(dry_run=True)[-1] == "--dry-run"


def test_stream_forwards_the_stream_flag():
    assert _argv(stream=True)[-1] == "--stream"


def test_dry_run_and_stream_together_are_refused():
    with pytest.raises(ValueError) as excinfo:
        cdc_catchup(dry_run=True, stream=True)
    message = str(excinfo.value)
    assert "dry_run" in message
    assert "stream" in message


def test_a_missing_script_fails_before_running_anything():
    with (
        mock.patch("ogip.tasks.cdc._CDC_SCRIPT", Path("/nonexistent/ingestr_cdc.sh")),
        mock.patch("ogip.tasks.cdc.subprocess.run") as run,
        pytest.raises(FileNotFoundError),
    ):
        cdc_catchup()
    run.assert_not_called()
