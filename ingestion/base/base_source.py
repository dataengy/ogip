"""Reusable ingestion abstractions (ADR-0006). `BaseSource` wraps **dlt** so each concrete
source stays small while landing raw Parquet under the Layer-0 contract `<system>__<table>`
with only `_ingested_at` + `etl_batch_id` added.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt


class BaseSource(ABC):
    """A source extracts records and lands them as raw Parquet via a dlt pipeline."""

    system: str  # e.g. "rawg"
    entity: str  # e.g. "games"

    @property
    def table_name(self) -> str:
        """Layer-0 raw table name: `<system>__<entity>`."""
        return f"{self.system}__{self.entity}"

    @abstractmethod
    def records(self) -> Iterator[dict[str, Any]]:
        """Yield source records (demonstrates pagination/retries/cache in subclasses)."""

    def run(self, data_dir: Path) -> Path:
        """Land the source as raw Parquet under ``data_dir/raw`` and return the table dir.

        Layout: ``<data_dir>/raw/<system>__<entity>/*.parquet`` (Layer-0, `<system>__<table>`).
        """
        batch_id = uuid.uuid4().hex
        ingested_at = datetime.now(UTC).isoformat()

        def _stamped() -> Iterator[dict[str, Any]]:
            for rec in self.records():
                yield {**rec, "_ingested_at": ingested_at, "etl_batch_id": batch_id}

        data_dir.mkdir(parents=True, exist_ok=True)
        pipeline = dlt.pipeline(
            pipeline_name=self.system,
            destination=dlt.destinations.filesystem(bucket_url=data_dir.resolve().as_uri()),
            dataset_name="raw",  # → <data_dir>/raw/<table>/
        )
        pipeline.run(
            _stamped(),
            table_name=self.table_name,
            loader_file_format="parquet",
            write_disposition="replace",
        )
        return data_dir / "raw" / self.table_name


class ApiSource(BaseSource):
    """Base for REST API sources (subclasses implement `records` with pagination/retries)."""


class ScraperSource(BaseSource):
    """Base for HTML/undocumented-JSON scrapers (land into Postgres `landing` first, D11)."""
