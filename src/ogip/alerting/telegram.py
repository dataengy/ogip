"""Telegram transport — Bot API ``sendMessage``.

Needs a bot token and a chat id (numeric, or ``@channelname``). ``topic_id`` targets one
topic of a forum supergroup.
"""

from __future__ import annotations

from typing import Any

from ogip.alerting._http import get_json, post_json
from ogip.alerting.base import split_message

__all__ = ["TelegramMessenger"]

_API_BASE = "https://api.telegram.org"
_MAX_LEN = 4096  # Telegram rejects longer messages outright


class TelegramMessenger:
    """Deliver alerts to a Telegram chat via the Bot API."""

    backend: str = "telegram"

    def __init__(
        self,
        token: str,
        chat_id: str,
        topic_id: int | None = None,
        *,
        parse_mode: str | None = None,
        api_base: str = _API_BASE,
    ) -> None:
        self.token = token
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.parse_mode = parse_mode
        self.api_base = api_base.rstrip("/")

    def _url(self, method: str) -> str:
        return f"{self.api_base}/bot{self.token}/{method}"

    def send(self, text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": self.chat_id, "text": text}
        if self.parse_mode:
            payload["parse_mode"] = self.parse_mode
        if self.topic_id is not None:
            payload["message_thread_id"] = self.topic_id
        return post_json(self._url("sendMessage"), payload)

    def send_long(self, text: str) -> list[dict[str, Any]]:
        return [self.send(chunk) for chunk in split_message(text, _MAX_LEN)]

    def check_health(self) -> bool:
        """``getMe`` — proves the token is valid without posting anything to the chat."""
        if not self.token or not self.chat_id:
            return False
        try:
            body = get_json(self._url("getMe"))
        except Exception:
            return False
        return bool(body.get("ok"))

    def __repr__(self) -> str:
        return f"TelegramMessenger(chat_id={self.chat_id!r}, topic_id={self.topic_id!r})"
