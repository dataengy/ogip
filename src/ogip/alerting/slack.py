"""Slack transport — Web API ``chat.postMessage``, or an incoming webhook.

Same two shapes as Mattermost: a bot token authenticates and can be health-checked; an
incoming webhook is unauthenticated and channel-bound. Bot token wins when both are set.

**The Slack gotcha**: the Web API answers ``HTTP 200`` even when the call failed, putting the
verdict in an ``ok`` field of the body (``{"ok": false, "error": "channel_not_found"}``). A
transport that only checked the status code would report every such failure as a success and
swallow the alert. :meth:`SlackMessenger.send` inspects ``ok`` and raises, so a dead Slack
config falls through to the fallback transport like any other failure.
"""

from __future__ import annotations

from typing import Any

from ogip.alerting._http import post_json
from ogip.alerting.base import split_message

__all__ = ["SlackMessenger", "SlackSendError"]

_API_POST = "https://slack.com/api/chat.postMessage"
_API_AUTH_TEST = "https://slack.com/api/auth.test"
_MAX_LEN = 3_900  # the text field allows far more, but Slack truncates past ~4k


class SlackSendError(RuntimeError):
    """Slack returned HTTP 200 with ``ok: false`` — a failure wearing a success's status."""


class SlackMessenger:
    """Deliver alerts to a Slack channel."""

    backend: str = "slack"

    def __init__(
        self,
        *,
        token: str = "",
        channel: str = "",
        webhook_url: str = "",
        username: str = "",
    ) -> None:
        self.token = token
        self.channel = channel
        self.webhook_url = webhook_url
        self.username = username

    @property
    def uses_api(self) -> bool:
        return bool(self.token and self.channel)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def send(self, text: str) -> dict[str, Any]:
        if self.uses_api:
            payload: dict[str, Any] = {"channel": self.channel, "text": text}
            if self.username:
                payload["username"] = self.username
            body = post_json(_API_POST, payload, headers=self._headers())
            if not body.get("ok"):
                raise SlackSendError(f"chat.postMessage failed: {body.get('error', body)}")
            return body
        if not self.webhook_url:
            raise ValueError("Slack is not configured — need token+channel, or webhook_url")
        # Webhooks answer with the literal string "ok"; a non-2xx already raised by here.
        return post_json(self.webhook_url, {"text": text})

    def send_long(self, text: str) -> list[dict[str, Any]]:
        return [self.send(chunk) for chunk in split_message(text, _MAX_LEN)]

    def check_health(self) -> bool:
        """API: ``auth.test``. Webhook: unverifiable without posting — report configured."""
        if self.uses_api:
            try:
                body = post_json(_API_AUTH_TEST, {}, headers=self._headers())
            except Exception:
                return False
            return bool(body.get("ok"))
        return bool(self.webhook_url)

    def __repr__(self) -> str:
        shape = "api" if self.uses_api else "webhook"
        return f"SlackMessenger(shape={shape!r}, channel={self.channel!r})"
