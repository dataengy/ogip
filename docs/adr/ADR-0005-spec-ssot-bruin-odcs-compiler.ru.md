<!-- ru-translation-of: docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md sha:c24ab0c4969f -->
<!-- Автоперевод. Источник — docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0005-spec-ssot-bruin-odcs-compiler.md](ADR-0005-spec-ssot-bruin-odcs-compiler.md)

# ADR-0005 — `spec/` как engine-agnostic SSoT: формат Bruin + ODCS + компилятор

- **Статус:** Принято
- **Дата:** 2026-07-17
- **Связано с:** D0/D5 · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Контекст

Движок — это выбор, поэтому спецификация не должна быть привязана ни к одному конкретному
движку. Мы также хотим, чтобы lineage, DQ, ownership и переносимый SQL жили в одном
читаемом месте.

## Решение

`spec/` — единственный источник истины. SQL пишется в **формате ассетов Bruin** (тело SQL +
`@bruin` YAML: `depends`→lineage, `columns[].checks`→DQ, `owner`/`tags`→метаданные);
контракты источников — в **ODCS**. Небольшой **компилятор спецификации**
(`src/ogip/spec_compile/`) рендерит спецификацию в native-проекты движков (SQLMesh по
умолчанию; dbt/Bruin для профилей сравнения). Для *чтения* спецификации бинарник движка не
требуется.

## Последствия

- Один файл на модель выражает SQL + lineage + DQ + ownership; движки взаимозаменяемы.
- Авторинг в Bruin + рантайм SQLMesh подразумевает шаг компиляции (принятая цена ради истории с SSoT).

## Рассмотренные альтернативы

- **Писать нативно в SQLMesh** — убирает компилятор, но привязывает спецификацию к одному движку.
- **Писать в dbt** — отклонено: запах «следующего dbt»; более слабая переносимость.
