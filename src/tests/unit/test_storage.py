"""Unit tests for the object-storage seam (no external services).

These pin the contract that makes `local`/`minio`/`s3`/`r2` one code path: the backend
decides the bucket URL and the credential shape, and nothing else in the pipeline changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ogip.config import get_settings
from ogip.storage import (
    BACKENDS,
    StorageBackendError,
    _credentials,
    configure_duckdb_s3,
    get_storage_settings,
    raw_bucket_url,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _reset_settings_caches() -> Iterator[None]:
    """Both settings singletons are lru_cached — rebuild them per test env."""
    get_storage_settings.cache_clear()
    get_settings.cache_clear()
    yield
    get_storage_settings.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def minio_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fully configured `minio` backend."""
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "minio")
    monkeypatch.setenv("OGIP_S3_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("OGIP_S3_ACCESS_KEY_ID", "ogipminio")
    monkeypatch.setenv("OGIP_S3_SECRET_ACCESS_KEY", "ogipminio123")


def test_backends_match_the_ssot_declaration() -> None:
    # config/config.yml documents exactly these four (D2) — drift here is a bug.
    assert BACKENDS == ("local", "minio", "s3", "r2")


def test_local_backend_is_the_default_and_not_object_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OGIP_STORAGE_BACKEND", raising=False)
    settings = get_storage_settings()
    assert settings.backend == "local"
    assert settings.is_object_storage is False


def test_local_backend_yields_a_file_uri(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "local")
    url = raw_bucket_url(tmp_path)
    assert url.startswith("file://")
    assert url == tmp_path.resolve().as_uri()


def test_raw_bucket_url_is_pure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Resolving a location must not create it — that is the caller's job.
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "local")
    target = tmp_path / "not-yet"
    raw_bucket_url(target)
    assert not target.exists()


@pytest.mark.usefixtures("minio_env")
def test_object_backend_yields_an_s3_url(tmp_path: Path) -> None:
    # The bucket URL ignores data_dir entirely once the lake is on object storage.
    assert raw_bucket_url(tmp_path) == "s3://ogip-raw"
    assert get_storage_settings().is_object_storage is True


@pytest.mark.usefixtures("minio_env")
def test_minio_uses_path_style_urls() -> None:
    # MinIO has no DNS-style bucket hosts; virtual-host addressing would 404.
    creds = _credentials("minio")
    assert creds.s3_url_style == "path"
    assert creds.endpoint_url == "http://localhost:9000"


def test_aws_s3_needs_no_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    # An empty endpoint means "real AWS" — resolved by region, not an error.
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("OGIP_S3_ENDPOINT_URL", "")
    monkeypatch.setenv("OGIP_S3_ACCESS_KEY_ID", "AKIAEXAMPLE")
    monkeypatch.setenv("OGIP_S3_SECRET_ACCESS_KEY", "secret")
    creds = _credentials("s3")
    assert creds.endpoint_url is None
    assert creds.s3_url_style == "auto"


def test_missing_credentials_explain_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "minio")
    monkeypatch.setenv("OGIP_S3_ACCESS_KEY_ID", "")
    monkeypatch.setenv("OGIP_S3_SECRET_ACCESS_KEY", "")
    with pytest.raises(StorageBackendError, match="OGIP_S3_ACCESS_KEY_ID"):
        _credentials("minio")


def test_r2_without_an_endpoint_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # R2 is only reachable via its account endpoint — failing early beats a cryptic 403.
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "r2")
    monkeypatch.setenv("OGIP_S3_ENDPOINT_URL", "")
    monkeypatch.setenv("OGIP_S3_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("OGIP_S3_SECRET_ACCESS_KEY", "secret")
    with pytest.raises(StorageBackendError, match=r"r2.*OGIP_S3_ENDPOINT_URL"):
        _credentials("r2")


def test_unknown_backend_in_the_ssot_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "gdrive")
    with pytest.raises(ValueError, match="gdrive"):
        get_storage_settings()


def test_configure_duckdb_is_a_noop_on_local(monkeypatch: pytest.MonkeyPatch) -> None:
    import duckdb

    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "local")
    con = duckdb.connect()
    try:
        configure_duckdb_s3(con)  # must not install httpfs or need credentials
        secrets = con.execute("select count(*) from duckdb_secrets()").fetchone()
        assert secrets is not None
        assert secrets[0] == 0
    finally:
        con.close()
