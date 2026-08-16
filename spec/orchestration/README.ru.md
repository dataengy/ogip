<!-- ru-translation-of: spec/orchestration/README.md sha:08c631f9074b -->
<!-- Автоперевод. Источник — spec/orchestration/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# spec/orchestration — ODOS 0.1 (Open Data Orchestration Standard)

SSoT оркестрации: *когда, в каком порядке и как это переживает сбой* — никогда не *что*
вычисляется (это ODTS, `spec/sql`). Один файл на группу; `_defaults.yml` сливается в
каждый джоб. Любой ключ, который ODOS не определяет, — ошибка компиляции (проектный документ, §4.9).

Компиляция: `just odos-compile` → `defs/orchestration/<group>.py` (Dagster — уплощённая
компоновка начиная с PR #34; `warehouse/` — подпакет, разбитый на jobs/schedules/sensors;
адаптер Prefect — план 3). Round-trip обеспечивается `src/tests/unit/test_odos_to_dagster.py`:
если вы правите эти файлы (или добавляете модель `spec/sql` — выборки разворачиваются
статически), перезапустите компиляцию и закоммитьте перегенерированный вывод.

Проектный документ: `docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md` · issue #37.
