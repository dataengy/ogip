"""Mattermost transport — REST bot token, or an incoming webhook.

Two shapes, picked per instance:

* **REST** (``url`` + ``token``) — ``POST /api/v4/posts``. Preferred: it authenticates, it
  reports real errors, and it can be health-checked. Posting needs an opaque ``channel_id``,
  so a human-readable channel *name* is resolved through the API first.
* **Incoming webhook** (``webhook_url``) — no token needed, but unauthenticated, unverifiable
  and channel-bound at the server. The fallback shape.

REST wins when both are configured.
"""

from __future__ import annotations

from typing import Any

from ogip.alerting._http import get_json, post_json
from ogip.alerting.base import split_message

__all__ = ["MattermostMessenger"]

_MAX_LEN = 16_000  # server caps a post at ~16383; leave room for the envelope
_CHANNEL_ID_LEN = 26  # Mattermost ids are 26-char strings — longer/shorter means it is a name


class MattermostMessenger:
    """Deliver alerts to a Mattermost channel."""

    backend: str = "mattermost"

    def __init__(
        self,
        *,
        url: str = "",
        token: str = "",
        team: str = "",
        channel: str = "",
        webhook_url: str = "",
        username: str = "",
    ) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.team = team
        self.channel = channel
        self.webhook_url = webhook_url
        self.username = username
        self._channel_id: str | None = None

    @property
    def uses_rest(self) -> bool:
        return bool(self.url and self.token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _resolve_channel_id(self) -> str:
        """Map a channel name to its id, once per instance.

        A value already shaped like an id is trusted as one — that is the only way to post
        to a channel whose team is not configured.
        """
        if self._channel_id:
            return self._channel_id
        if len(self.channel) == _CHANNEL_ID_LEN:
            self._channel_id = self.channel
            return self._channel_id
        if not self.team:
            raise ValueError(
                f"channel {self.channel!r} is a name, not an id — set `team` so it can be resolved"
            )
        body = get_json(
            f"{self.url}/api/v4/teams/name/{self.team}/channels/name/{self.channel}",
            headers=self._headers(),
        )
        channel_id = body.get("id")
        if not isinstance(channel_id, str):
            raise ValueError(f"could not resolve Mattermost channel {self.channel!r}")
        self._channel_id = channel_id
        return channel_id

    def send(self, text: str) -> dict[str, Any]:
        if self.uses_rest:
            payload: dict[str, Any] = {"channel_id": self._resolve_channel_id(), "message": text}
            return post_json(f"{self.url}/api/v4/posts", payload, headers=self._headers())
        if not self.webhook_url:
            raise ValueError("Mattermost is not configured — need url+token, or webhook_url")
        hook_payload: dict[str, Any] = {"text": text}
        if self.channel:
            hook_payload["channel"] = self.channel
        if self.username:
            hook_payload["username"] = self.username
        return post_json(self.webhook_url, hook_payload)

    def send_long(self, text: str) -> list[dict[str, Any]]:
        return [self.send(chunk) for chunk in split_message(text, _MAX_LEN)]

    def check_health(self) -> bool:
        """REST: verify the token. Webhook: unverifiable without posting — report configured."""
        if self.uses_rest:
            try:
                body = get_json(f"{self.url}/api/v4/users/me", headers=self._headers())
            except Exception:
                return False
            return "id" in body
        return bool(self.webhook_url)

    def __repr__(self) -> str:
        shape = "rest" if self.uses_rest else "webhook"
        return f"MattermostMessenger(shape={shape!r}, channel={self.channel!r})"
