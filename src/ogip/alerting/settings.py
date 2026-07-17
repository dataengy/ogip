"""Alerting settings — credentials and routing.

Deviates from the project's SSoT layering on purpose, and temporarily. The norm is
``config/config.yml`` → rendered ``.env`` → typed settings (see ``ogip.config``), but both
``config/config.yml`` and ``config/.env-render.py`` belong to the ``core-pipeline`` lane and
are edited by another session. So routing defaults live here for now and every knob is
env-overridable; folding them into the SSoT is a one-section handoff recorded in
``.ai/STATUS.md``.

Names stay ``OGIP_``-prefixed. Bare ``TELEGRAM_*``/``SLACK_*`` would be friendlier to read
and would collide with anything else on the box that reads the same ``.env`` — the same trap
that already bit ``PREFECT_API_URL`` (see ``config/.env-render.py``).
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "AlertingSettings",
    "MattermostSettings",
    "SlackSettings",
    "TelegramSettings",
]

_ENV_FILE = ".env"


def _config(prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=prefix,
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class TelegramSettings(BaseSettings):
    """``OGIP_TG_*`` — bot token + target chat."""

    model_config = _config("OGIP_TG_")

    bot_token: SecretStr | None = None
    chat_id: str = ""
    topic_id: int | None = None
    parse_mode: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


class MattermostSettings(BaseSettings):
    """``OGIP_MM_*`` — REST (url + token + channel) or an incoming webhook."""

    model_config = _config("OGIP_MM_")

    url: str = ""
    token: SecretStr | None = None
    team: str = ""
    channel: str = ""
    webhook_url: SecretStr | None = None
    username: str = ""

    @property
    def is_configured(self) -> bool:
        return bool((self.url and self.token and self.channel) or self.webhook_url)


class SlackSettings(BaseSettings):
    """``OGIP_SLACK_*`` — bot token (+ channel) or an incoming webhook."""

    model_config = _config("OGIP_SLACK_")

    token: SecretStr | None = None
    channel: str = ""
    webhook_url: SecretStr | None = None
    username: str = ""

    @property
    def is_configured(self) -> bool:
        return bool((self.token and self.channel) or self.webhook_url)


class AlertingSettings(BaseSettings):
    """``OGIP_ALERT_*`` — which transport delivers, and which catches it when it fails.

    ``fallback_backend`` empty means no fallback: one failed send, one failed alert. Set it
    to a *different* backend than ``backend`` — a fallback on the same transport retries the
    thing that just broke.
    """

    model_config = _config("OGIP_ALERT_")

    backend: str = "telegram"
    fallback_backend: str = ""
    dry_run: bool = False
