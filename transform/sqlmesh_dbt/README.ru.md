<!-- ru-translation-of: transform/sqlmesh_dbt/README.md sha:f879e36f6339 -->
<!-- Автоперевод. Источник — transform/sqlmesh_dbt/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `transform/sqlmesh_dbt/` — СГЕНЕРИРОВАНО из `spec/` (не редактировать вручную)

Профиль `prefect-sqlmesh-over-dbt`: тот же сгенерированный dbt-проект, что и `transform/dbt/`,
плюс `config.py`, чтобы SQLMesh загружал его нативно. Перегенерация: `just spec-compile sqlmesh-dbt`.
Запуск из корня репозитория: `uv run --group engines sqlmesh -p transform/sqlmesh_dbt plan`.
