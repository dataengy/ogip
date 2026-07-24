"""dlt loads for the Dagster lane — RAWG → raw Parquet (Layer 0).

Mirrors `ingestion/sources/rawg.py`: dlt is the ingestion engine (ADR-0006 / D11) and demo
mode reads the synthetic fixture, so the asset graph runs with zero credentials. The landed
layout matches the platform contract — `<data_dir>/raw/<system>__<entity>/*.parquet` — so the
dbt `raw.rawg__games` model reads exactly what the Prefect lane produces.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt

# .../<worktree>/experimental/orchestration/dagster_ogip/src/dagster_ogip/defs/dlt_ingest/loads.py
REPO = Path(__file__).resolve().parents[7]
FIXTURE = REPO / "ingestion" / "samples" / "rawg_games.json"
DATA_DIR = REPO / ".run" / "data"


@dlt.source(name="rawg")
def rawg_source() -> Any:
    # file_format pinned on the RESOURCE: dagster-dlt calls `pipeline.run()` itself (no
    # loader_file_format arg), so the filesystem destination would otherwise default to JSONL.
    # The raw contract is Parquet, and the dbt/SQLMesh `read_parquet` model depends on it.
    @dlt.resource(name="rawg__games", write_disposition="replace", file_format="parquet")
    def rawg__games() -> Iterator[dict[str, Any]]:
        batch_id = uuid.uuid4().hex
        ingested_at = datetime.now(UTC).isoformat()
        records: Any = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for record in records:
            yield {**record, "_ingested_at": ingested_at, "etl_batch_id": batch_id}

    return rawg__games


rawg_load_source = rawg_source()
rawg_load_pipeline = dlt.pipeline(
    pipeline_name="rawg",
    destination=dlt.destinations.filesystem(bucket_url=DATA_DIR.resolve().as_uri()),
    dataset_name="raw",  # → <data_dir>/raw/rawg__games/*.parquet
)
