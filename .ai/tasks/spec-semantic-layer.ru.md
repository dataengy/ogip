<!-- ru-translation-of: .ai/tasks/spec-semantic-layer.md sha:5ba8f1ac51ee -->
<!-- Автоперевод. Источник — .ai/tasks/spec-semantic-layer.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [spec-semantic-layer.md](spec-semantic-layer.md)

# Задача — `spec/`: описание семантического слоя, не зависящее от движка (Bruin Semantic Layer)

**Статус:** 📋 запланировано · **Приоритет:** средний

Lane: `spec`. Область: `spec/`. Issue: [#20](https://github.com/dataengy/ogip/issues/20).
Часть трека SSoT `spec/` ([PLAN](../PLAN.md) A2 · A4): семантические *фреймворки* остаются в
`experimental/semantic/` (демо MetricFlow/Cube) и потребляют `spec/`, поэтому сами семантические
*определения* принадлежат агностичному слою спецификации.

## Цель

Описать семантический слой OGIP — сущности, измерения, меры/метрики поверх моделей
CORE/STAR/AM/MARTS — **внутри `spec/`, независимо от движка**, в формате
[Bruin Semantic Layer](https://getbruin.com/docs/bruin/core-concepts/semantic-layer.html#semantic-layer).
Согласуется с D0: спецификация пишется в открытой сериализации Bruin; Bruin остаётся
форматом авторинга, а не продакшен-зависимостью.

## Набросок

- [ ] Изучить формат Bruin Semantic Layer (ссылка на доку выше) — сверить точный синтаксис в момент
      авторинга, согласно заметке A2.
- [ ] Добавить `spec/semantic/` (или расширить метаданные Bruin-ассетов) с описанием сущностей ·
      измерений · мер — сначала для моделей среза M0.
- [ ] Сохранить потребляемость из `experimental/semantic/` (демо MetricFlow/Cube, фаза 9) и
      компилятором спецификации; без зависимости на продакшен-пути.
- [ ] Задокументировать в README `spec/` + сослаться из PLAN A2 после приземления.

## Критерии приёмки

- Семантические определения живут в `spec/` как данные (YAML семантического слоя Bruin), читаемые
  без бинарника какого-либо движка.
- Демо в `experimental/semantic/` (когда будут построены) потребляют их, а не переопределяют метрики заново.
