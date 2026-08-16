<!-- ru-translation-of: spec/ODOS/examples/README.md sha:abdc3a08c6db -->
<!-- Автоперевод. Источник — spec/ODOS/examples/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Пример соответствия ODOS 0.1

Эти семь YAML-файлов — ODOS-проекция шестигрупповой модели оркестрации, определённой в
руководящем проектном документе: общие значения по умолчанию плюс warehouse, ingestion,
snapshots, maintenance, integrations и monitoring.

Это примеры стандарта, а не живой SSoT оркестрации OGIP. Будущие живые документы принадлежат
строчному `spec/orchestration/` и компилируются в проекты Dagster и Prefect.

`just standards-validate` валидирует каждый файл по `../schema.json` и проверяет локальные
ссылки на джобы и партиции.
