<!-- ru-translation-of: spec/sources/README.md sha:0d96300384b5 -->
<!-- Автоперевод. Источник — spec/sources/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `spec/sources/` — дескрипторы доступа к источникам данных (ГЕНЕРИРУЕТСЯ)

**Каждый файл здесь сгенерирован — не редактируйте.** Каждый дескриптор — односторонняя
проекция из SSoT реестра инжестии (`~/.ai/skills/.settings/de/ingestion/sources/`),
проштампованная заголовком DO-NOT-EDIT и командой перегенерации. Жёсткие ссылки (hardlink)
SSoT↔проекция были на практике признаны небезопасными (`git checkout` разрывает inode, и копии
тихо расходятся) — отсюда проекция.

## Что это такое (в отличие от `spec/contracts/`)

| Дерево | Отвечает на вопрос | Пример содержимого |
|---|---|---|
| `spec/contracts/` | чем данные **ЯВЛЯЮТСЯ** | схема ODCS, правила качества, SLA, владение |
| `spec/sources/` | как до них **ДОБРАТЬСЯ** и **МОЖНО ЛИ** | url, слоты auth, tier, вердикты robots/ToS (дословно, с датой), измеренные лимиты запросов, ловушки, форма инжестии `dlt:`/`scrape:`/`airbyte:`, аудиторский след `provenance:` |

Вердикты (KEYLESS-VERIFIED, SCRAPE-VERIFIED, FORBIDDEN, …) **никогда не хранятся** — они
заново доказываются вживую пробой при каждой проверке. Сохранённый вердикт гниёт и
превращается в ложь; дескрипторы несут *доказательства и их дату*, а не вывод.

## Область охвата

OGIP получает **только область games** (`--area games`). Реестр несёт и другие области
(например, cinema) для других проектов — их эмиссия сюда — баг, а не фича.

## Команды (Justfile реестра: `~/.ai/skills/_scripts/de/ingestion/Justfile`)

```sh
JF=~/.ai/skills/_scripts/de/ingestion/Justfile
just -f "$JF" probe <key>              # live-verify one source (real GET, real verdict)
just -f "$JF" probe-all                # the pre-flight sweep
just -f "$JF" spec-emit-check . games  # drift gate: exit 1 if these files are stale
just -f "$JF" spec-emit . games        # regenerate after editing the registry
```

## Чтение дескриптора

Порядок доверия: `traps:` (измеренные режимы отказа) > `robots:`/`license_note:` (дословно,
с датой — перепроверьте, если устарело) > всё остальное. `do_not_fetch: true` означает, что
проба отказывается открывать соединение; источник может быть технически достижим и всё равно
запрещён (HLTB, SteamDB — дословные запреты см. в их `license_note:`). `publishable: false`
защищает *данные*; `do_not_fetch` защищает *получение* — это независимые шлюзы.
