"""Object-storage seam — resolves the configured backend to a concrete lake location.

D2 / [ADR-0003](../../docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md): the raw
Parquet lake lives on the local filesystem (default) or on S3-compatible object storage.
``minio`` (local dev), ``s3`` (AWS) and ``r2`` (Cloudflare, cloud of record) share **one**
code path — only endpoint, credentials and URL style differ — so switching profile never
changes pipeline code.

SSoT layering (mirrors :mod:`ogip.config`):

- **which** backend → ``config/config.yml → storage.backend``, overridable via
  ``OGIP_STORAGE_BACKEND`` (rendered into ``.env`` by ``config/.env-render.py``).
- **where/how** → :class:`ogip.config.S3Settings` (``OGIP_S3_*``): endpoint, bucket,
  region, credentials.

Callers use :func:`raw_bucket_url` + :func:`dlt_filesystem_destination` to write, and
:func:`configure_duckdb_s3` to read ``s3://`` Parquet from DuckDB.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal, get_args

from dlt.destinations import filesystem
from dlt.sources.credentials import AwsCredentials
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ogip.config import get_settings, load_app_config

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection

Backend = Literal["local", "minio", "s3", "r2", "gcs", "yc"]
BACKENDS: tuple[Backend, ...] = get_args(Backend)

# MinIO is deployed without DNS-style bucket hosts, so it needs path-style URLs
# (`endpoint/bucket/key`); AWS S3, R2, GCS (interoperability/XML API) and Yandex Cloud
# Object Storage all use the default virtual-host style.
_PATH_STYLE_BACKENDS: frozenset[Backend] = frozenset({"minio"})

# One DuckDB secret name, replaced on every configure — keeps re-runs idempotent.
_DUCKDB_SECRET = "ogip_s3"


class StorageBackendError(RuntimeError):
    """The configured storage backend is unknown, or is missing its credentials."""


def _default_backend() -> Backend:
    """Read the backend default from the SSoT (config/config.yml)."""
    value = str(load_app_config()["storage"]["backend"])
    if value not in BACKENDS:
        raise StorageBackendError(
            f"config/config.yml → storage.backend = {value!r} is not one of {list(BACKENDS)}"
        )
    return value


class StorageSettings(BaseSettings):
    """Which lake backend is active (``OGIP_STORAGE_BACKEND``; default from config.yml)."""

    model_config = SettingsConfigDict(
        env_prefix="OGIP_STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    backend: Backend = Field(default_factory=_default_backend)

    @property
    def is_object_storage(self) -> bool:
        """True when the lake is on S3-compatible storage rather than the local FS."""
        return self.backend != "local"


@lru_cache(maxsize=1)
def get_storage_settings() -> StorageSettings:
    return StorageSettings()


# Backends that address a specific host: without an endpoint there is nothing to talk to.
# Plain `s3` may omit it — an empty endpoint means "real AWS", resolved by region. GCS and
# Yandex Cloud each expose one fixed S3-compatible host, so both require an endpoint too.
_ENDPOINT_REQUIRED: frozenset[Backend] = frozenset({"minio", "r2", "gcs", "yc"})

_ENDPOINT_HINT: dict[Backend, str] = {
    "minio": "http://localhost:${MINIO_API_PORT} — see `make storage-up`",
    "r2": "https://<account-id>.r2.cloudflarestorage.com",
    "gcs": "https://storage.googleapis.com",
    "yc": "https://storage.yandexcloud.net",
}


def _credentials(backend: Backend) -> AwsCredentials:
    """Build dlt credentials for an S3-compatible backend, or explain what is missing."""
    s3 = get_settings().s3
    # `is_configured` proves both are set, but does not narrow them for the type checker.
    if s3.access_key_id is None or s3.secret_access_key is None or not s3.is_configured:
        raise StorageBackendError(
            f"storage backend {backend!r} needs OGIP_S3_ACCESS_KEY_ID and "
            "OGIP_S3_SECRET_ACCESS_KEY — fill them in .env (see `make render-env`). "
            "For local MinIO run `make storage-up`, which prints the dev keys."
        )
    if backend in _ENDPOINT_REQUIRED and not s3.endpoint_url:
        raise StorageBackendError(
            f"storage backend {backend!r} needs OGIP_S3_ENDPOINT_URL ({_ENDPOINT_HINT[backend]})"
        )
    return AwsCredentials(
        aws_access_key_id=s3.access_key_id,
        aws_secret_access_key=s3.secret_access_key.get_secret_value(),
        endpoint_url=s3.endpoint_url or None,  # None → real AWS S3, resolved by region
        region_name=s3.region,
        s3_url_style="path" if backend in _PATH_STYLE_BACKENDS else "auto",
    )


def raw_bucket_url(data_dir: Path) -> str:
    """dlt ``bucket_url`` for the raw zone (Layer 0).

    ``local`` → a ``file://`` URI under ``data_dir``; otherwise ``s3://<raw_bucket>``.
    Pure: creating the local directory is the caller's job.
    """
    settings = get_storage_settings()
    if not settings.is_object_storage:
        return data_dir.resolve().as_uri()
    return f"s3://{get_settings().s3.raw_bucket}"


def dlt_filesystem_destination(data_dir: Path) -> filesystem:
    """The dlt filesystem destination for the active backend (raw Parquet lands here)."""
    settings = get_storage_settings()
    bucket_url = raw_bucket_url(data_dir)
    if not settings.is_object_storage:
        return filesystem(bucket_url=bucket_url)
    return filesystem(bucket_url=bucket_url, credentials=_credentials(settings.backend))


def configure_duckdb_s3(con: DuckDBPyConnection) -> None:
    """Let DuckDB read ``s3://`` Parquet: load ``httpfs`` + register the S3 secret.

    No-op on the ``local`` backend. Credentials are **bound parameters**, never
    interpolated into SQL. Safe to call repeatedly (the secret is replaced).
    """
    settings = get_storage_settings()
    if not settings.is_object_storage:
        return
    creds = _credentials(settings.backend)
    con.execute("install httpfs; load httpfs;")

    fields = ["type s3", "key_id ?", "secret ?", "region ?", "url_style ?"]
    params: list[object] = [
        creds.aws_access_key_id,
        creds.aws_secret_access_key,
        creds.region_name,
        creds.s3_url_style,
    ]
    if creds.endpoint_url:
        # DuckDB wants a bare `host:port` — it rejects a scheme-qualified endpoint —
        # and infers nothing about TLS from it, so pass `use_ssl` explicitly.
        fields += ["endpoint ?", "use_ssl ?"]
        params += [
            creds.endpoint_url.removeprefix("https://").removeprefix("http://"),
            not creds.endpoint_url.startswith("http://"),
        ]
    # Only `fields` (fixed literals) reaches the SQL text; every value is bound.
    con.execute(
        f"create or replace secret {_DUCKDB_SECRET} ({', '.join(fields)})",
        params,
    )
