"""Typed configuration — the single entry point for all settings.

Layering (strict SSoT, see config/README.md):

1. **`config/config.yml`** — single source of truth for every non-secret default
   (paths, endpoints, buckets, ports, profiles). Loaded here directly.
2. **Environment / root `.env`** — overrides + secrets only. The flat `.env` is
   rendered from `config/config.yml` by ``config/.env-render.py``; blank values are
   ignored (``env_ignore_empty``), so empty override slots never shadow YAML defaults.
   Secret slots are filled by hand (default) or GitHub Actions secrets in CI (ADR-0011).

Credential groups report ``is_configured == False`` when unset — callers skip that
source or fall back to demo mode instead of failing.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = ".env"


class ConfigFileMissingError(RuntimeError):
    """config/config.yml could not be located (see OGIP_CONFIG)."""


@lru_cache(maxsize=1)
def load_app_config() -> dict[str, Any]:
    """Load config/config.yml — from $OGIP_CONFIG or by walking up from cwd."""
    override = os.environ.get("OGIP_CONFIG")
    if override:
        candidates = [Path(override)]
    else:
        cwd = Path.cwd()
        candidates = [parent / "config" / "config.yml" for parent in (cwd, *cwd.parents)]
    for candidate in candidates:
        if candidate.is_file():
            data: Any = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ConfigFileMissingError(f"{candidate} is not a YAML mapping")
            return cast("dict[str, Any]", data)
    raise ConfigFileMissingError(
        "config/config.yml not found — run from the repo, or set OGIP_CONFIG"
    )


def _yaml(section: str, key: str) -> Any:
    return load_app_config()[section][key]


def _config(prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=prefix,
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class PlatformSettings(BaseSettings):
    """Platform-wide knobs: local paths and logging."""

    model_config = _config("OGIP_")

    data_dir: Path = Field(default_factory=lambda: Path(str(_yaml("platform", "data_dir"))))
    log_dir: Path = Field(default_factory=lambda: Path(str(_yaml("platform", "log_dir"))))
    log_level: str = Field(default_factory=lambda: str(_yaml("platform", "log_level")))
    log_json: bool = Field(default_factory=lambda: bool(_yaml("platform", "log_json")))

    @property
    def warehouse_path(self) -> Path:
        return self.data_dir / "warehouse" / "ogip.duckdb"

    @property
    def log_file(self) -> Path:
        """Rolling application log — under .run/logs, never the repo root."""
        return self.log_dir / "ogip.log"

    @property
    def raw_local_dir(self) -> Path:
        """Filesystem raw zone (Layer 0) used when object storage is not configured."""
        return self.data_dir / "raw"

    @property
    def outputs_dir(self) -> Path:
        """ML-ready output datasets (*.parquet)."""
        return self.data_dir / "outputs"


class S3Settings(BaseSettings):
    """Object storage: local FS by default; MinIO locally, Cloudflare R2 in cloud."""

    model_config = _config("OGIP_S3_")

    endpoint_url: str = Field(default_factory=lambda: str(_yaml("storage", "endpoint_url")))
    access_key_id: str | None = None
    secret_access_key: SecretStr | None = None
    raw_bucket: str = Field(default_factory=lambda: str(_yaml("storage", "raw_bucket")))
    region: str = Field(default_factory=lambda: str(_yaml("storage", "region")))

    @property
    def is_configured(self) -> bool:
        return bool(self.access_key_id and self.secret_access_key)


class PostgresSettings(BaseSettings):
    """Postgres roles (ADR-0008): ``landing`` schema + ``platform_meta`` + Prefect backend."""

    model_config = _config("OGIP_PG_")

    host: str = Field(default_factory=lambda: str(_yaml("postgres", "host")))
    port: int = Field(default_factory=lambda: int(_yaml("postgres", "port")))
    user: str = Field(default_factory=lambda: str(_yaml("postgres", "user")))
    database: str = Field(default_factory=lambda: str(_yaml("postgres", "database")))
    password: SecretStr | None = None  # secret: .env only (demo value via .env-render.py)

    @property
    def dsn(self) -> str:
        if self.password is None:
            raise RuntimeError(
                "OGIP_PG_PASSWORD is not set — render .env first: "
                "uv run python config/.env-render.py"
            )
        pwd = self.password.get_secret_value()
        return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.database}"


class SteamSettings(BaseSettings):
    model_config = _config("STEAM_")

    api_key: SecretStr | None = None

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None


class RawgSettings(BaseSettings):
    model_config = _config("RAWG_")

    api_key: SecretStr | None = None

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None


class IgdbSettings(BaseSettings):
    """IGDB authenticates via Twitch OAuth2 client-credentials."""

    model_config = _config("IGDB_")

    client_id: str | None = None
    client_secret: SecretStr | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


class Settings:
    """Aggregate of all setting groups, built once via :func:`get_settings`."""

    def __init__(self) -> None:
        self.platform = PlatformSettings()
        self.s3 = S3Settings()
        self.pg = PostgresSettings()
        self.steam = SteamSettings()
        self.rawg = RawgSettings()
        self.igdb = IgdbSettings()

    @property
    def demo_mode(self) -> bool:
        """True when no source credentials are configured at all.

        Demo mode runs the full pipeline from bundled sample data instead of live
        extraction — no API keys needed for a first run.
        """
        sources = (self.steam, self.rawg, self.igdb)
        return not any(source.is_configured for source in sources)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
