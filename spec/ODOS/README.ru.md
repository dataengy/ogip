<!-- ru-translation-of: spec/ODOS/README.md sha:862196908d0c -->
<!-- Автоперевод. Источник — spec/ODOS/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# ODOS — Open Data Orchestration Standard

Этот каталог — нормативный **профиль ODOS 0.1** OGIP, извлечённый из утверждённого
[проектного документа ODOS](../../docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md).
ODOS описывает, когда выполняется работа, в каком порядке и как она переживает сбой. Он не
описывает сами трансформации.

Файлы:

- [`SPEC.md`](SPEC.md) — нормативная семантика и требования соответствия;
- [`schema.json`](schema.json) — JSON Schema с закрытым словарём для ODOS YAML;
- [`examples/`](examples/) — шестигрупповая модель соответствия OGIP плюс значения по умолчанию;
- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — реализация OGIP
  (`experimental/orchestration/dagster_ogip/` · `pipelines/flows/` · `src/ogip/tasks/`),
  описанная в терминах стандарта.

Пакет не зависит от движка и читается без Dagster и Prefect. Схема валидирует форму
документа; валидация компилятора дополнительно разрешает имена задач, выборки активов,
перекрёстные ссылки, возможности целей, партиции и выведенный из ODTS граф активов.

Запустите `just standards-validate`, чтобы провалидировать схему и примеры.
