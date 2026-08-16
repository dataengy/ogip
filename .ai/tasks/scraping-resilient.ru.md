<!-- ru-translation-of: .ai/tasks/scraping-resilient.md sha:d03ef90c664a -->
<!-- Автоперевод. Источник — .ai/tasks/scraping-resilient.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [scraping-resilient.md](scraping-resilient.md)

# Задача — Устойчивый скрейпинг: `ScraperSource` + landing + первый скрейпленный источник (~~HLTB~~ → Metacritic)

**Статус:** 🟡 **SLICE-ONLY** (walking-slice выпущен; устойчивый слой отложен) · **Приоритет:** **P1**

> **Аудит 2026-07-27** (`/audit-feature-implementation-and-integration`): **walking-slice
> ГОТОВ и интегрирован end-to-end** — `ScraperSource` (синхронный) + четыре источника (Metacritic,
> OpenCritic, PSN, SteamCharts) `fetch → raw Parquet`, подключённые через `@odos_task ingest.<src>` /
> `ingest.scraped` в каждый run-профиль, с контрактами ODCS, моделями raw+staging и зелёными
> unit-тестами. **Отложено = устойчивый слой** из раздела «Ожидаемые результаты» ниже: асинхронная
> конкурентность, politeness-троттлинг/backoff, circuit breaker + DLQ, effectively-once upsert в Postgres `landing`,
> watermark'и, CPU-пул парсинга, наблюдаемость fetch'а. Признание в коде:
> `src/ogip/tasks/ingest.py: ingest.parse_to_landing` — плейсхолдер «wire the async
> ScraperSource here». Список результатов ниже сформулирован под HLTB, но цель заменена на
> Metacritic (см. заметку ⛔); пункты устойчивости не зависят от движка и остаются без изменений.

> **⛔ 2026-07-18 — HLTB юридически заблокирован; первый скрейпленный источник теперь Metacritic.**
> robots.txt HowLongToBeat (Ziff Davis) прямо запрещает автоматизированное получение данных и называет
> AI/ML-базы и шаринг датасетов запрещёнными применениями — OGIP публикует ML-ready
> датасеты, так что это дисквалифицирует источник независимо от `publishable: false` (он защищает
> данные, а не fetch). Доказательство + дословная цитата:
> [`spec/sources/games/hltb_games.yaml`](../../spec/sources/games/hltb_games.yaml)
> (`do_not_fetch: true` — проба возвращает FORBIDDEN, не открывая соединения).
> Metacritic — запланированный ниже всего лишь как «следующий после» — разрешён robots для `/game/`,
> и его скрейп-контракт проверен вживую (JSON-LD, 6/6 полей):
> [`spec/sources/games/metacritic_game.yaml`](../../spec/sources/games/metacritic_game.yaml).
> SteamCharts (css-маркеры) и OpenCritic (JSON-LD) тоже проверены пробой и готовы.
> Данным о длительности игр нужна лицензированная или разрешённая замена (licensing@ziffdavis.com, либо
> поля IGDB/Wikidata) — отслеживается в бэклоге. Всё остальное в этой задаче
> (ScraperSource, landing, politeness, устойчивость) остаётся без изменений; меняется только целевой
> источник.

Lane: `ingestion` (перед записью захватить lock-объект). Скоуп:
`ingestion/base/scraper_source.py`, `ingestion/common/{http,throttle,cache,watermark}.py`,
`ingestion/sources/hltb.py`, DDL для landing, тесты. Запись решения:
[ADR-0014](../../docs/adr/ADR-0014-resilient-scraping-concurrency.md) · паттерн landing:
[ADR-0006](../../docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md) · открытые
вопросы: [OPEN-QUESTIONS §1](../../docs/OPEN-QUESTIONS.md).

## Почему

Половина запланированных источников — скрейпленные/парсенные, и устойчивый скрейпинг — самый
большой разрыв между заявленной архитектурой (PLAN A6) и выпущенным кодом — M0 покрывает только
чистый API. Этот слайс делает половину пайплайна `scrape → Postgres landing → dlt → raw Parquet`
реальной, с полным паттерном устойчивости, который переиспользует каждый последующий скрейпленный источник.

> **Slice 1 выпущен (2026-07-20)** — walking skeleton скрейп-пути, Metacritic-first:
> `ingestion/common/http.py` (PoliteFetcher: глобальные + по-доменные лимиты, разнесение с минимальным
> интервалом, экспоненциальный backoff с учётом Retry-After, идентифицирующий UA, таймауты, деградация вместо смерти) ·
> `ingestion/base/scraper_source.py` (контракт urls()/parse(); politeness из конфиг-SSoT) ·
> `ingestion/sources/metacritic.py` (извлечение JSON-LD по контракту spec/sources;
> демо = встроенная фикстура, live за флагом OGIP_METACRITIC_LIVE=1 — скрейпинг реального сайта
> никогда не бывает тихим побочным эффектом `make run`) · конфиг-блок `scraping:` · 9 unit-тестов ·
> `make run` зелёный e2e с приземлённым Parquet `metacritic__game` (Hades/93/61 проверено).
> **Ещё открыто ↓**: хоп Postgres `landing` + идемпотентный upsert (записи уже несут natural
> key + content_hash), circuit breaker, DLQ, watermark, пул парсинга, счётчики по источникам,
> контракт ODCS + `stg_metacritic__game`, интеграционный тест на записанных ответах.

## Ожидаемые результаты

- [ ] **`ScraperSource` (async)** — `httpx.AsyncClient`; глобальная + по-доменная ограниченная
      конкурентность из конфиг-SSoT (`scraping.max_connections` · `scraping.per_domain`).
- [ ] **Politeness** — по-доменный token-bucket-троттлинг; backoff tenacity с джиттером,
      учитывающий `Retry-After`; идентифицирующий User-Agent; заметка о robots/ToS фиксируется в
      контракте источника.
- [ ] **Устойчивость** — таймауты на каждом вызове; бюджет ретраев на URL; по-доменный circuit
      breaker (cooldown, прогон продолжается в деградированном режиме); DLQ-таблица `landing.fetch_failures`
      (url, attempts, last_error, fetched_at) + путь повторного проигрывания.
- [ ] **Effectively-once landing** — идемпотентный upsert по natural key + content hash
      (`ON CONFLICT` update); watermark-чекпоинты, чтобы прерванные проходы возобновлялись.
- [ ] **Опциональный CPU-пул парсинга** — чистые функции парсинга; `ProcessPoolExecutor` за
      `scraping.parse_workers` (дефолт `0` = inline).
- [ ] **Наблюдаемость** — структурированные fetch-события в потоке JSON-логов; счётчики по
      источникам (fetched · retried · failed · rate-limited · breaker-open); хуки алертов на свежесть +
      долю ошибок (`Notifier`).
- [ ] **`ingestion/sources/hltb.py`** — обнаружение сущностей (id игр уже в raw) →
      fetch → парсинг (часы main / extra / completionist) → landing.
- [ ] **dlt-загрузка** — landing → raw `hltb__games` Parquet (merge/dedupe по natural key).
- [ ] **spec-продолжение** — контракт ODCS + модель `stg_hltb__games`.
- [ ] **Тесты** — unit на фикстурах, без живого HTTP в CI (троттлинг, backoff, breaker,
      идемпотентный upsert: одна и та же страница дважды → одна строка); один интеграционный тест на
      записанном ответе; e2e: флоу прогоняет scrape (фикстуры) → landing → raw → stg зелёным в CI.

## Приёмка

- `make run` (HLTB включён на фикстурах) зелёный end to end; повторный запуск ничего не дублирует
  ни в landing, ни в raw.
- Убить прогон посреди прохода → следующий прогон возобновляется с watermark, без дубликатов.
- Домен, принудительно падающий N раз, открывает breaker; прогон завершается и сообщает о
  деградации домена вместо краха.
- `make check` зелёный; CI зелёный.

## Следующее после этого

Metacritic как второй скрейпленный источник (тот же паттерн; первая проверка на лестнице
враждебных сайтов), затем региональные ценовые проходы (API-shaped, враждебные по объёму) — см.
[sources-backlog.md](sources-backlog.md).
