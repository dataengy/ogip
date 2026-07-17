"""Unit tests for the flow-failure alerting hook (no Prefect run, no network)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from pipelines import alerting_hooks
from pipelines.alerting_hooks import notify_flow_failure


# Duck-typed stand-ins for Prefect's Flow / FlowRun / State — the hook only reads .name/.message.
@dataclass
class _Flow:
    name: str = "ingest_transform_publish"


@dataclass
class _FlowRun:
    name: str = "brave-otter"


@dataclass
class _State:
    message: str | None = "boom: sqlmesh plan exited 1"
    name: str = "Failed"


@dataclass
class _Notifier:
    """Records the delivered text; `ok` toggles the falsy-result path."""

    ok: bool = True
    sent: list[str] = field(default_factory=list[str])
    error: str = "transport down"

    def notify(self, text: str) -> object:
        self.sent.append(text)
        return _Result(self.ok, "" if self.ok else self.error)


@dataclass
class _Result:
    sent: bool
    error: str = ""

    def __bool__(self) -> bool:
        return self.sent


def test_failure_alert_carries_flow_run_and_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Notifier()
    monkeypatch.setattr(alerting_hooks, "make_notifier", lambda: recorder)

    notify_flow_failure(_Flow(), _FlowRun(), _State())

    assert len(recorder.sent) == 1
    msg = recorder.sent[0]
    assert "ingest_transform_publish" in msg
    assert "brave-otter" in msg
    assert "sqlmesh plan exited 1" in msg


def test_no_credentials_sends_nothing_and_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alerting_hooks, "make_notifier", lambda: None)
    # Must be a no-op, not an error: a credential-free pipeline fails as it always did.
    notify_flow_failure(_Flow(), _FlowRun(), _State())


def test_hook_never_raises_even_if_notifier_construction_explodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> object:
        raise RuntimeError("env parse blew up")

    monkeypatch.setattr(alerting_hooks, "make_notifier", _boom)
    # A failure hook that raised would mask the real flow failure — it must swallow this.
    notify_flow_failure(_Flow(), _FlowRun(), _State())


def test_undelivered_alert_is_logged_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _Notifier(ok=False)
    monkeypatch.setattr(alerting_hooks, "make_notifier", lambda: recorder)

    notify_flow_failure(_Flow(), _FlowRun(), _State())  # falsy result → warn, no raise

    assert recorder.sent  # it tried


def test_reason_falls_back_to_state_name_when_message_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Notifier()
    monkeypatch.setattr(alerting_hooks, "make_notifier", lambda: recorder)

    notify_flow_failure(_Flow(), _FlowRun(), _State(message=None))

    assert "Failed" in recorder.sent[0]  # used state.name since message was None
