# shellcheck shell=bash
# SSoT for the generated dbt project's location — the directory NAME, relative to this
# subproject's root (experimental/orchestration/dagster_ogip/).
#
# spec/ is the SSoT for the dbt project's CONTENT (ADR-0005); this is the SSoT for WHERE the
# compiler writes it and where every consumer reads it: jobs/dg-tasks.sh, e2e/run_combo.sh, the
# dagster-e2e GitHub workflow, and docs/runbooks/run-dagster.md all source this instead of
# hardcoding "dbt". Change the layout in one place.
#
# The DbtProjectComponent (src/dagster_ogip/defs/dbt_ingest/defs.yaml) uses `{{ project_root }}/dbt`
# — component YAML cannot source shell, so that literal is the one intentional twin of this value;
# a comment there points back here. Keep the two in sync.
export DBT_PROJECT_DIR="${DBT_PROJECT_DIR:-dbt}"
