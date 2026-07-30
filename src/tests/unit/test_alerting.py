"""Unit tests for the alerting layer (no network — httpx is mocked with respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from ogip.alerting import (
    MattermostMessenger,
    Notifier,
    SlackMessenger,
    SlackSendError,
    TelegramMessenger,
    make_messenger,
    make_notifier,
    split_message,
)

# ── split_message ───────────────────────────────────────────────────────────


def test_short_message_is_not_split() -> None:
    assert split_message("hello", 100) == ["hello"]


def test_split_prefers_line_boundaries() -> None:
    text = "\n".join(f"line {i}" for i in range(10))
    chunks = split_message(text, 20)
    assert all(len(c) <= 20 for c in chunks)
    assert "".join(chunks) == text  # nothing lost, nothing duplicated


def test_single_overlong_line_is_hard_wrapped() -> None:
    chunks = split_message("x" * 250, 100)
    assert [len(c) for c in chunks] == [100, 100, 50]
    assert "".join(chunks) == "x" * 250


def test_split_rejects_a_nonsense_limit() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        split_message("x", 0)


# ── Telegram ────────────────────────────────────────────────────────────────


@respx.mock
def test_telegram_send_posts_expected_payload() -> None:
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )
    TelegramMessenger("TOKEN", "@chan", 42).send("boom")

    assert route.called
    assert route.calls.last.request.read() == (
        b'{"chat_id":"@chan","text":"boom","message_thread_id":42}'
    )


@respx.mock
def test_telegram_splits_oversized_message_into_several_posts() -> None:
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    TelegramMessenger("TOKEN", "1").send_long("y" * 5000)  # over the 4096 cap

    assert route.call_count == 2


@respx.mock
def test_telegram_health_is_false_when_token_is_rejected() -> None:
    respx.get("https://api.telegram.org/botBAD/getMe").mock(return_value=httpx.Response(401))
    assert TelegramMessenger("BAD", "1").check_health() is False


# ── Slack ───────────────────────────────────────────────────────────────────


@respx.mock
def test_slack_raises_on_ok_false_despite_http_200() -> None:
    """The Slack gotcha: a failed call still answers 200, with the verdict in the body."""
    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(200, json={"ok": False, "error": "channel_not_found"})
    )
    with pytest.raises(SlackSendError, match="channel_not_found"):
        SlackMessenger(token="T", channel="#nope").send("boom")


@respx.mock
def test_slack_webhook_shape_is_used_without_a_token() -> None:
    route = respx.post("https://hooks.slack.com/services/XXX").mock(
        return_value=httpx.Response(200, text="ok")
    )
    messenger = SlackMessenger(webhook_url="https://hooks.slack.com/services/XXX")

    assert messenger.uses_api is False
    assert messenger.send("boom") == {"raw": "ok"}  # webhooks answer text, not JSON
    assert route.called


def test_slack_without_any_config_refuses_to_send() -> None:
    with pytest.raises(ValueError, match="not configured"):
        SlackMessenger().send("boom")


# ── Mattermost ──────────────────────────────────────────────────────────────


@respx.mock
def test_mattermost_rest_resolves_channel_name_then_posts() -> None:
    lookup = respx.get("https://mm.example.com/api/v4/teams/name/t/channels/name/alerts").mock(
        return_value=httpx.Response(200, json={"id": "c" * 26})
    )
    post = respx.post("https://mm.example.com/api/v4/posts").mock(
        return_value=httpx.Response(201, json={"id": "p1"})
    )
    messenger = MattermostMessenger(
        url="https://mm.example.com", token="T", team="t", channel="alerts"
    )
    messenger.send("boom")
    messenger.send("boom again")

    assert lookup.call_count == 1, "channel id should be resolved once and cached"
    assert post.call_count == 2


def test_mattermost_needs_a_team_to_resolve_a_channel_name() -> None:
    messenger = MattermostMessenger(url="https://mm.example.com", token="T", channel="alerts")
    with pytest.raises(ValueError, match="set `team`"):
        messenger.send("boom")


@respx.mock
def test_mattermost_channel_id_is_used_as_is() -> None:
    post = respx.post("https://mm.example.com/api/v4/posts").mock(
        return_value=httpx.Response(201, json={"id": "p1"})
    )
    MattermostMessenger(url="https://mm.example.com", token="T", channel="c" * 26).send("boom")

    assert post.called  # no team lookup needed


# ── Notifier ────────────────────────────────────────────────────────────────


class _Recorder:
    """Minimal Messenger stub: records what it was asked to send, or explodes on demand."""

    def __init__(self, backend: str, *, fail: bool = False) -> None:
        self.backend = backend
        self.fail = fail
        self.sent: list[str] = []

    def send(self, text: str) -> dict[str, object]:
        return self.send_long(text)[0]

    def send_long(self, text: str) -> list[dict[str, object]]:
        if self.fail:
            raise RuntimeError(f"{self.backend} is down")
        self.sent.append(text)
        return [{"ok": True}]

    def check_health(self) -> bool:
        return not self.fail


def test_dry_run_reports_instead_of_sending() -> None:
    recorder = _Recorder("telegram")
    result = Notifier(recorder, dry_run=True).notify("boom")

    assert not result
    assert result.reason == "dry_run"
    assert recorder.sent == []


def test_failed_send_returns_a_result_rather_than_raising() -> None:
    result = Notifier(_Recorder("telegram", fail=True)).notify("boom")

    assert not result
    assert "telegram is down" in result.error


def test_fallback_delivers_and_stays_visible_in_the_result() -> None:
    primary, fallback = _Recorder("telegram", fail=True), _Recorder("mattermost")
    result = Notifier(primary, fallback=fallback).notify("boom")

    assert result  # the alert was NOT lost
    assert result.backend == "mattermost"  # ...but not by the transport we asked for
    assert "telegram" in result.reason
    assert fallback.sent == ["boom"]


def test_both_transports_down_reports_both_errors() -> None:
    result = Notifier(
        _Recorder("telegram", fail=True), fallback=_Recorder("mattermost", fail=True)
    ).notify("boom")

    assert not result
    assert "telegram is down" in result.error
    assert "mattermost is down" in result.error


def test_notify_if_changed_skips_none() -> None:
    recorder = _Recorder("telegram")
    result = Notifier(recorder).notify_if_changed(None)

    assert not result
    assert result.reason == "no change"
    assert recorder.sent == []


# ── factory ─────────────────────────────────────────────────────────────────


def test_unknown_backend_is_a_config_typo_not_a_missing_secret() -> None:
    with pytest.raises(ValueError, match="unknown alerting backend"):
        make_messenger("carrier-pigeon")


def test_alerting_is_off_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OGIP_TG_BOT_TOKEN", "OGIP_TG_CHAT_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OGIP_ALERT_DRY_RUN", "false")

    assert make_notifier() is None


def test_dry_run_works_with_no_credentials_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OGIP_TG_BOT_TOKEN", raising=False)
    notifier = make_notifier(dry_run=True)

    assert notifier is not None
    assert not notifier.notify("boom")  # previewed, never sent


def test_configured_telegram_builds_a_notifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OGIP_TG_BOT_TOKEN", "TOKEN")
    monkeypatch.setenv("OGIP_TG_CHAT_ID", "-100")

    notifier = make_notifier(backend="telegram", dry_run=False)

    assert notifier is not None
    assert notifier.messenger.backend == "telegram"


def test_fallback_naming_the_primary_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OGIP_TG_BOT_TOKEN", "TOKEN")
    monkeypatch.setenv("OGIP_TG_CHAT_ID", "-100")

    notifier = make_notifier(backend="telegram", fallback_backend="telegram")

    assert notifier is not None
    assert notifier.fallback is None  # retrying the broken transport is not a fallback
