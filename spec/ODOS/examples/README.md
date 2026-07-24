# ODOS 0.1 conformance example

These seven YAML files are the ODOS projection of the six-group orchestration model defined in
the governing design: shared defaults plus warehouse, ingestion, snapshots, maintenance,
integrations, and monitoring.

They are examples of the standard, not OGIP's live orchestration SSoT. The future live documents
belong under lowercase `spec/orchestration/` and compile into Dagster and Prefect projects.

`just standards-validate` validates every file against `../schema.json` and checks local job and
partition references.
