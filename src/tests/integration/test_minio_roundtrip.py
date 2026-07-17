"""Integration: the raw zone really round-trips through S3-compatible object storage.

Proves the `minio` profile end to end — dlt **writes** raw Parquet to `s3://`, DuckDB
**reads** it back via `httpfs` — which is the same code path `s3` and `r2` take (only the
endpoint and credentials differ, D2 / ADR-0003).

Needs MinIO: `make storage-up`. Excluded from the CI unit job by the `integration` marker.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any

import dlt
import duckdb
import pytest

from ogip.config import get_settings
from ogip.storage import configure_duckdb_s3, dlt_filesystem_destination, get_storage_settings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytestmark = pytest.mark.integration

MINIO_HOST, MINIO_PORT = "localhost", 9000
TABLE = "storage_it__widgets"
RECORDS: list[dict[str, Any]] = [
    {"id": 1, "name": "alpha", "price": 9.99},
    {"id": 2, "name": "beta", "price": 19.5},
    {"id": 3, "name": "gamma", "price": 0.0},
]


def _minio_is_up() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((MINIO_HOST, MINIO_PORT)) == 0


@pytest.fixture(autouse=True)
def minio_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not _minio_is_up():
        pytest.skip(f"MinIO not reachable on {MINIO_HOST}:{MINIO_PORT} — run `make storage-up`")
    monkeypatch.setenv("OGIP_STORAGE_BACKEND", "minio")
    monkeypatch.setenv("OGIP_S3_ENDPOINT_URL", f"http://{MINIO_HOST}:{MINIO_PORT}")
    monkeypatch.setenv("OGIP_S3_ACCESS_KEY_ID", "ogipminio")
    monkeypatch.setenv("OGIP_S3_SECRET_ACCESS_KEY", "ogipminio123")
    get_storage_settings.cache_clear()
    get_settings.cache_clear()
    yield
    get_storage_settings.cache_clear()
    get_settings.cache_clear()


def test_dlt_writes_raw_parquet_to_minio_and_duckdb_reads_it_back(tmp_path: Path) -> None:
    bucket = get_settings().s3.raw_bucket

    # --- write: exactly what BaseSource.run does, via the storage seam ---
    pipeline = dlt.pipeline(
        pipeline_name="ogip_storage_it",
        destination=dlt_filesystem_destination(tmp_path),
        dataset_name="raw",
        pipelines_dir=str(tmp_path / "dlt"),
    )
    pipeline.run(
        RECORDS, table_name=TABLE, loader_file_format="parquet", write_disposition="replace"
    )

    # Nothing may leak onto the local FS when the lake is remote.
    assert not (tmp_path / "raw").exists()

    # --- read: DuckDB over httpfs against the same object storage ---
    con = duckdb.connect()
    try:
        configure_duckdb_s3(con)
        rows = con.execute(
            f"select id, name, price from read_parquet('s3://{bucket}/raw/{TABLE}/*.parquet') "
            "order by id"
        ).fetchall()
    finally:
        con.close()

    assert [(r[0], r[1], r[2]) for r in rows] == [
        (rec["id"], rec["name"], rec["price"]) for rec in RECORDS
    ]


def test_configure_duckdb_s3_is_idempotent() -> None:
    # The flow may configure a connection more than once per run; re-registering must not throw.
    con = duckdb.connect()
    try:
        configure_duckdb_s3(con)
        configure_duckdb_s3(con)
        secrets = con.execute(
            "select count(*) from duckdb_secrets() where name = 'ogip_s3'"
        ).fetchone()
        assert secrets is not None
        assert secrets[0] == 1
    finally:
        con.close()
