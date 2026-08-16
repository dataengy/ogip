<!-- ru-translation-of: docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md sha:cc6589e524c8 -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-20-source-dod-registry-and-domain-docs.md](2026-07-20-source-dod-registry-and-domain-docs.md)

# Source Definition-of-Done, истина реестра и документы бизнес-домена — План реализации

> **Для агентских исполнителей:** ОБЯЗАТЕЛЬНЫЙ САБ-СКИЛЛ: Используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Goal:** Закрыть долг по источнику Metacritic, сделать Definition of Done исполняемым гейтом вместо прозы, зафиксировать находки исследования источников от 2026-07-20 как истину реестра и дать OGIP словарь и документацию бизнес-домена, которых у него сейчас нет.

**Architecture:** Шесть независимых задач, упорядоченных так, чтобы верификация каждой была осмысленной. Задача 1 гасит долг; Задача 2 устанавливает проверку, которая останавливает его повторение (она не может пройти до приземления Задачи 1, в чём и суть); Задачи 3–6 — документация и истина реестра, каждая отгружаема независимо.

**Tech Stack:** Контракты ODCS v3 (`spec/contracts/`) · переносимый SQL `@bruin` (`spec/sql/`) · внерепозиторный реестр ингестии (`~/.ai/skills/.settings/de/ingestion/`) · bash + `prek` для гейта · `/update-terms-glossaries` для глоссариев · `gh` для issue.

## Глобальные ограничения

- **Дисциплина полос.** Захватите lock перед записью: `bash src/scripts/lane.sh acquire <lane> "<reason>"`. Используемые здесь полосы: `ingestion` (Задачи 1–2), `spec` (SQL Задачи 1), `docs` (Задачи 4–5). Ветку разделяют четыре и более агентских сессий.
- **Никогда `git add -A`.** Параллельные сессии оставляют застейдженные файлы в общем индексе. Используйте `git commit -o <paths>`.
- **Каждый коммит несёт `Refs: #<n>` или `Closes: #<n>`** — принудительно через `.ci/steps/commit-binding.sh`.
- **Никогда не делайте force-push** `dev` или `main`.
- **Этот репозиторий ПУБЛИЧНЫЙ.** Запустите `bash src/scripts/public-hygiene.sh` перед отгрузкой любой прозы.
- **`spec/sources/*.yaml` ГЕНЕРИРУЕТСЯ.** Никогда его не правьте. Правьте SSoT реестра в `~/.ai/skills/.settings/de/ingestion/sources/games/<key>.yml`, затем переизлучите.
- **`spec/sql/` сегодня использует заголовок `@bruin`.** ADR-0016 мигрирует его на `@odts`, но это приземляется с [#35](https://github.com/dataengy/ogip/issues/35). Сопоставляйте соседний `stg_games.sql` — не мигрируйте вручную один файл впереди флота.
- **Закон Layer-0:** raw — это `<system>__<entity>`, 1:1 AS-IS, и единственные добавленные столбцы — `_ingested_at` и `etl_batch_id`. Приведение типов и переименование относятся к staging.
- **Работа с реестром происходит в другом репозитории** (`~/.ai/skills/`) и нуждается в собственном коммите — она не часть какого-либо коммита OGIP.

---

### Task 1: ODCS-контракт Metacritic + staging-модель

Коммит `dc02ddb` поставил `ingestion/sources/metacritic.py` и приземлил Parquet `raw/metacritic__game`, но без контракта и без staging-модели. Сырая таблица сейчас ничего не питает.

**Files:**
- Create: `spec/contracts/metacritic/metacritic__game.odcs.yaml`
- Create: `spec/sql/staging/stg_metacritic__game.sql`
- Reference (do not modify): `spec/contracts/rawg/rawg__games.odcs.yaml`, `spec/sql/staging/stg_games.sql`, `ingestion/sources/metacritic.py:74-92`

**Interfaces:**
- Consumes: форму записи, испускаемую `MetacriticGame._record()` — `slug`, `content_hash`, `source_url`, `name`, `released`, `genre`, `publisher`, `metascore`, `review_count`; плюс `_ingested_at` и `etl_batch_id`, добавляемые `BaseSource.run`.
- Produces: `staging.stg_metacritic__game` с ключевым столбцом `game_slug`, потребляемый любой более поздней моделью `core.*`.

- [ ] **Step 1: Подтвердите сырую форму, прежде чем писать контракт**

Не переписывайте из исходного кода в одиночку — проверьте, что реально приземлилось.

```bash
make run
python3 -c "
import duckdb, glob
f = sorted(glob.glob('.run/data/raw/metacritic__game/**/*.parquet', recursive=True))
print('files:', f)
con = duckdb.connect()
print(con.execute(f\"describe select * from read_parquet('{f[0]}')\").fetchdf())
print(con.execute(f\"select * from read_parquet('{f[0]}')\").fetchdf())
"
```

Ожидается: одна строка (Hades, metascore 93, review_count 61, publisher "Supergiant Games") и ровно 9 столбцов записи плюс `_ingested_at` и `etl_batch_id`. Если набор столбцов отличается от списка в **Interfaces** выше, контракт следует *реальности*, а не этому плану — и скажите об этом в теле коммита.

- [ ] **Step 2: Напишите ODCS-контракт**

Создайте `spec/contracts/metacritic/metacritic__game.odcs.yaml`:

```yaml
# Open Data Contract Standard (ODCS) v3 — Metacritic game pages, Layer-0 raw dataset.
apiVersion: v3.0.0
kind: DataContract
id: metacritic-game-raw
name: metacritic__game
version: 0.1.0
status: draft
domain: games
tenant: ogip
description:
  purpose: Immutable 1:1 AS-IS capture of the schema.org VideoGame JSON-LD on Metacritic game pages (Layer 0).
  usage: Source for staging.stg_metacritic__game — the quality dimension (critic aggregate).
  limitations: >
    NOT PUBLISHABLE. robots.txt permits /game/ (verified 2026-07-18) but the Metacritic/Fandom
    Terms of Use have not been reviewed for redistribution of critic aggregates; see
    spec/sources/games/metacritic_game.yaml. Demo mode parses a synthetic fixture; live mode is
    gated behind OGIP_METACRITIC_LIVE=1.

servers:
  - server: local-fs
    type: local
    format: parquet
    path: .run/data/raw/metacritic__game/

schema:
  - name: metacritic__game
    logicalType: object
    physicalType: parquet
    properties:
      - name: slug
        logicalType: string
        required: true
        unique: true
        description: Page slug from the URL — the natural key.
      - name: content_hash
        logicalType: string
        required: true
        description: SHA-256 of the raw JSON-LD block; the landing-upsert change signal.
      - name: source_url
        logicalType: string
        required: true
        description: The page this record was extracted from.
      - name: name
        logicalType: string
        required: true
      - name: released
        logicalType: date
        description: schema.org datePublished.
      - name: genre
        logicalType: string
      - name: publisher
        logicalType: string
        description: First entry of the JSON-LD publisher array.
      - name: metascore
        logicalType: integer
        description: Metascore (0-100) from aggregateRating.ratingValue.
      - name: review_count
        logicalType: integer
        description: aggregateRating.reviewCount.
      - name: _ingested_at
        logicalType: string
        description: Layer-0 ingestion timestamp (ISO-8601 UTC).
      - name: etl_batch_id
        logicalType: string
        description: Layer-0 batch id.

quality:
  - rule: unique
    property: slug
    severity: error
  - rule: not_null
    property: name
    severity: error
  - rule: not_null
    property: content_hash
    severity: error

slaProperties:
  - property: freshness
    value: 7
    unit: d
    element: metacritic__game._ingested_at

team:
  - username: data-eng@ogip
    role: owner
```

Обратите внимание: SLA свежести — 7d, а не 1d как у RAWG: агрегат критиков для вышедшего тайтла почти статичен, и SLA в 1d алертил бы на непроблему.

- [ ] **Step 3: Напишите staging-модель**

Создайте `spec/sql/staging/stg_metacritic__game.sql`. Точно сопоставьте `stg_games.sql` по стилю заголовка и SQL-раскладке с ведущими запятыми:

```sql
/* @bruin
name: staging.stg_metacritic__game
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, metacritic, daily]
depends:
  - raw.metacritic__game
columns:
  - name: game_slug
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: metascore
    type: integer
@bruin */
select
    slug as game_slug
    , name
    , try_cast(released as date) as released_date
    , genre
    , publisher
    , cast(metascore as integer) as metascore
    , cast(review_count as integer) as review_count
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.metacritic__game
```

- [ ] **Step 4: Проверьте, что модель компилируется и запускается**

```bash
make check
make run
```

Ожидается: `make check` зелёный (ruff, pyright strict, pytest). `make run` строит `staging.stg_metacritic__game` с одной строкой и без провалов проверок. Если раннер не подхватывает модель автоматически, найдите, как зарегистрирован `stg_games`, и зарегистрируйте эту так же — не делайте для неё частный случай.

- [ ] **Step 5: Коммит**

```bash
bash src/scripts/public-hygiene.sh
git add spec/contracts/metacritic/metacritic__game.odcs.yaml spec/sql/staging/stg_metacritic__game.sql
git commit -o spec/contracts/metacritic/metacritic__game.odcs.yaml spec/sql/staging/stg_metacritic__game.sql -F - <<'EOF'
feat(spec): ODCS contract + staging model for metacritic__game

Repays the debt from dc02ddb: the ScraperSource slice landed raw Parquet
with neither a contract nor a consumer, so the raw table fed nothing and
no gate noticed.

Freshness SLA is 7d (not RAWG's 1d) — a critic aggregate for a released
title is near-static.

Closes: #18
EOF
```

---

### Task 2: Сделать Definition of Done исполняемым гейтом

Правило «контракт + тест поставляются с коннектором» существовало в `/add-data-source` как проза, одной секцией выше кода, который её игнорировал. Проза — не гейт.

**Files:**
- Create: `.ci/steps/source-dod.sh`
- Modify: `Justfile` (рецепты `check:` и `ci:`), `config/.pre-commit-config.yaml`, `.github/workflows/ci.yml`
- Test: `src/tests/unit/test_source_dod_check.py`

Гейт — это **CI-шаг**, а не свободный скрипт: этот репозиторий маршрутизирует каждый гейт через `.ci/run.sh <step>` с телом шага в `.ci/steps/<step>.sh`, так что GitHub Actions и локальные прогоны выполняют идентичный код. `src/scripts/` — для операторского инструментария; гейт, который CI обязан гонять, принадлежит `.ci/steps/`.

**Interfaces:**
- Consumes: блок `sources:` в `config/config.yml` (список включённых источников), `spec/contracts/`, `spec/sql/staging/`. Переопределение корня для тестов: `SOURCE_DOD_ROOT`.
- Produces: exit 0, когда у каждого включённого источника есть контракт и staging-модель; exit 1 с отчётом на источник, называющим отсутствующий артефакт.

- [ ] **Step 1: Напишите падающий тест**

Создайте `src/tests/unit/test_source_dod_check.py`:

```python
"""The source Definition-of-Done gate: every enabled source needs a contract + staging model."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".ci" / "steps" / "source-dod.sh"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "SOURCE_DOD_ROOT": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_passes_on_the_real_repo() -> None:
    """Every source enabled in config.yml has its contract and staging model."""
    result = _run(REPO)
    assert result.returncode == 0, result.stdout + result.stderr


def test_names_the_missing_artifact(tmp_path: Path) -> None:
    """A source with no contract fails loudly and names what is missing."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yml").write_text(
        "sources:\n  ghost:\n    enabled: true\n    entities: [thing]\n", encoding="utf-8"
    )
    (tmp_path / "spec" / "contracts").mkdir(parents=True)
    (tmp_path / "spec" / "sql" / "staging").mkdir(parents=True)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ghost__thing" in result.stdout
    assert "contract" in result.stdout.lower()


def test_disabled_sources_are_not_required(tmp_path: Path) -> None:
    """`enabled: false` is the documented way to park an aspirational source."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yml").write_text(
        "sources:\n  ghost:\n    enabled: false\n    entities: [thing]\n", encoding="utf-8"
    )
    (tmp_path / "spec" / "contracts").mkdir(parents=True)
    (tmp_path / "spec" / "sql" / "staging").mkdir(parents=True)

    assert _run(tmp_path).returncode == 0
```

- [ ] **Step 2: Запустите тест, чтобы убедиться, что он падает**

```bash
uv run pytest src/tests/unit/test_source_dod_check.py -v
```

Ожидается: FAIL — скрипт ещё не существует (`bash: .../source-dod-check.sh: No such file`).

- [ ] **Step 3: Напишите скрипт**

Создайте `.ci/steps/source-dod.sh`. Подключите `_common.sh` как каждый другой шаг — он устанавливает `set -euo pipefail`, разрешает `REPO_ROOT`, делает `cd` туда и предоставляет `log`:

```bash
#!/usr/bin/env bash
# Source Definition-of-Done gate — every ENABLED source in config/config.yml must have an
# ODCS contract and a staging model. Exists because the rule lived in prose and was skipped:
# metacritic__game landed as raw Parquet with neither, and nothing failed.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

ROOT="${SOURCE_DOD_ROOT:-$REPO_ROOT}"
CONFIG="$ROOT/config/config.yml"
CONTRACTS="$ROOT/spec/contracts"
STAGING="$ROOT/spec/sql/staging"

die() { echo "[ci] ERROR: $*" >&2; exit 2; }

[[ -f "$CONFIG" ]] || die "no config at $CONFIG"

# Emit "<system> <entity>" per enabled source. Python, not awk: the config is YAML, and a
# regex over nested YAML is how silent misparses get shipped.
mapfile -t PAIRS < <(python3 - "$CONFIG" <<'PY'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
for system, spec in (cfg.get("sources") or {}).items():
    if not (spec or {}).get("enabled"):
        continue
    for entity in (spec or {}).get("entities") or []:
        print(f"{system} {entity}")
PY
)

failed=0
for pair in "${PAIRS[@]}"; do
    read -r system entity <<<"$pair"
    table="${system}__${entity}"

    if [[ ! -f "$CONTRACTS/$system/$table.odcs.yaml" ]]; then
        log "MISSING contract  $table  → expected $CONTRACTS/$system/$table.odcs.yaml"
        failed=1
    fi
    if [[ ! -f "$STAGING/stg_$table.sql" && ! -f "$STAGING/stg_$system.sql" ]]; then
        log "MISSING staging   $table  → expected $STAGING/stg_$table.sql"
        failed=1
    fi
done

if [[ "$failed" -eq 0 ]]; then
    log "source-dod: OK — ${#PAIRS[@]} enabled source(s), all contracted and consumed"
    exit 0
fi

log ""
log "A source that lands raw Parquet with no contract and no consumer is a demo, not a source."
log "See /add-data-source Step 4 — Definition of Done."
exit 1
```

Обратите внимание, что проверка staging принимает и `stg_<system>.sql`: `rawg__games` потребляется `stg_games.sql`, и гейт должен описывать существующий репозиторий, а не навязывать переименование.

- [ ] **Step 4: Запустите тесты, чтобы убедиться, что они проходят**

```bash
chmod +x .ci/steps/source-dod.sh
uv run pytest src/tests/unit/test_source_dod_check.py -v
bash .ci/run.sh source-dod
```

Ожидается: все три теста PASS. Прямой прогон печатает `source-dod: OK` — но **только если Задача 1 приземлилась**. Если он сообщает `MISSING contract metacritic__game`, гейт работает, а Задача 1 не завершена. Обратите внимание: `steam` включён в `config.yml` с сущностями `[games, reviews]` и вовсе не имеет коннектора: если гейт его отмечает, это истинная находка — либо запись конфига аспирационна и должна быть `enabled: false`, либо источник действительно должен быть. Разрешите это явно; не ослабляйте гейт, чтобы это скрыть.

- [ ] **Step 5: Подключите гейт в `check`, `ci`, prek-хуки и GitHub Actions**

`Justfile` — **оспариваемый файл** — `ship.sh` отказывает в нём, если вы не держите его object lock. Захватите его:

```bash
bash ~/.ai/skills/_scripts/session/agent-session-lock.sh acquire --repo . \
  --object Justfile --reason "wire source-dod gate into check"
```

Четыре правки. Читайте каждый файл непосредственно перед правкой — они двигаются под вами.

1. `Justfile` — добавьте рецепт и поместите его в цепочку `check`:

```just
check: lint typecheck test source-dod

# Every enabled source has an ODCS contract and a staging model
source-dod:
    bash .ci/run.sh source-dod
```

2. `Justfile` — добавьте шаг в рецепт `ci:`, чтобы локальный паритет CI оставался точным:

```just
    bash .ci/run.sh source-dod
```

3. `config/.pre-commit-config.yaml` — добавьте в существующий блок `repo: local`, по образцу уже имеющихся там записей `ty` / `pytest-smoke`:

```yaml
      - id: source-dod
        name: source Definition-of-Done (contract + staging per enabled source)
        entry: bash .ci/run.sh source-dod
        language: system
        pass_filenames: false
        files: '^(config/config\.yml|spec/(contracts|sql/staging)/)'
```

4. `.github/workflows/ci.yml` — добавьте `source-dod` рядом с другими шагами `.ci/run.sh`. Если workflow перечисляет шаги в матрице, добавьте его в матрицу, а не как отдельную job.

- [ ] **Step 6: Коммит**

```bash
bash src/scripts/public-hygiene.sh
make check
PATHS=".ci/steps/source-dod.sh src/tests/unit/test_source_dod_check.py Justfile config/.pre-commit-config.yaml .github/workflows/ci.yml"
git add $PATHS
git commit -o $PATHS -F - <<'EOF'
ci(sources): executable Definition-of-Done gate for data sources

Every enabled source in config.yml must have an ODCS contract and a staging
model. The rule already existed in /add-data-source as prose and was skipped
anyway — dc02ddb shipped metacritic__game with neither and no gate noticed.

Refs: #18
EOF
```

---

### Task 3: Зафиксировать находки исследования источников от 2026-07-20 как истину реестра

Исследование 2026-07-20 дало четыре вердикта FORBIDDEN, один неразрешённый конфликт robots и свидетельство, что одна ступень лестницы эскалации ADR-0014 не имеет легитимного сценария использования. Ничто из этого не зафиксировано, поэтому следующий агент выведет это заново.

**Files (registry — the `~/.ai/skills/` repository, separate commit):**
- Create: `~/.ai/skills/.settings/de/ingestion/sources/games/{epic_store_product,kickstarter_project,gamalytic_game,mobygames_credits}.yml`

**Files (OGIP):**
- Modify: `.ai/tasks/sources-backlog.md` (строки 8 и 12), `.ai/FIXME.md` (новая запись), `docs/adr/ADR-0014-resilient-scraping-concurrency.md`
- Generated, do not hand-edit: `spec/sources/games/*.yaml`

- [ ] **Step 1: Зарегистрируйте четыре запрещённых источника**

Смоделируйте каждый по существующему `hltb_games.yml` — устоявшаяся форма для записи-запрета. Каждой нужны `do_not_fetch: true`, `license:`, начинающийся с `FORBIDDEN-`, `license_note:`, цитирующий свидетельство **дословно с его датой**, и блок `provenance:`. Вердикты, все проверены 2026-07-20:

| key | url | evidence to quote |
|---|---|---|
| `epic_store_product` | `https://store.epicgames.com/` | `robots.txt` сам возвращает **HTTP 403** — страницу-испытание Cloudflare (25,353 B, `Enable JavaScript and cookies to continue`). Документ разрешений нечитаем, поэтому грант на извлечение установить нельзя. |
| `kickstarter_project` | `https://www.kickstarter.com/` | `robots.txt` возвращает **HTTP 403** интерстишл Cloudflare (`<title>Just a moment...</title>`). Подтверждает находку бэклога от 2026-07-18. |
| `gamalytic_game` | `https://gamalytic.com/` | `robots.txt` возвращает страницу-испытание `Vercel Security Checkpoint`. |
| `mobygames_credits` | `https://www.mobygames.com/` | robots.txt несёт `Content-Signal: search=yes,ai-train=no,use=reference` с явной оговоркой Article 4 / EU Directive 2019/790, **и** отдельные `User-agent: ClaudeBot` / `Disallow: /`. `ai-train=no` целится ровно в то, что OGIP отгружает. |

Для `mobygames_credits` зафиксируйте честный предел свидетельства: их страница `/info/api/` вернула 403 на автоматическое извлечение, так что условия **API** — юридически отдельные от контент-сигналов сайта — не были прочитаны. Запись блокирует *скрейп*; человек, читающий условия API в браузере, всё ещё мог бы разблокировать API. Не подавайте вердикт по сайту как вердикт по API.

- [ ] **Step 2: Валидируйте и переизлучите проекцию**

```bash
JF=~/.ai/skills/_scripts/de/ingestion/Justfile
just -f "$JF" split-check
just -f "$JF" probe-all          # FORBIDDEN entries must NOT be fetched — verify that in the output
just -f "$JF" route-all          # each new entry must route to `none` [forbidden]
just -f "$JF" spec-emit /Users/nk.myg/gi/@dataengy/OGIP games
just sources-drift
```

Ожидается: `route-all` показывает четыре новых ключа как `none [forbidden]`; `probe-all` не открывает к ним соединений; `sources-drift` выходит с 0.

- [ ] **Step 3: Перепишите две устаревшие строки бэклога**

В `.ai/tasks/sources-backlog.md` строка 8 (MobyGames) сейчас читается как открытый кандидат, а строка 12 (Kickstarter) — как мягкое предупреждение. Обе теперь заблокированы. Перепишите их в устоявшемся стиле строк HLTB и SteamDB — зачеркните имя источника, `⛔ FORBIDDEN` со ссылкой на зарегистрированный дескриптор и укажите, какое измерение остаётся непокрытым. Для MobyGames это **production budget / team size**, которое теряет своего главного кандидата.

Добавьте строку под «Grooming rules», фиксирующую, что нашёл прочёс: обнаруженные им разрешённые кандидаты (Nintendo eShop, Xbox Store, GOG) все серверно-рендерятся или являются чистым REST — полезны, но ни один из них не оправдывает новый уровень извлечения.

- [ ] **Step 4: Зафиксируйте неразрешённый конфликт robots Steam в реестре FIXME**

Добавьте запись **F9** в `.ai/FIXME.md`, и в таблицу индекса, и в тело. Провал, изложенный как провал:

`steam_applist` зарегистрирован как `tier: direct`, `publishable: true`, маршрутизируется в `dlt` и сидит на `api.steampowered.com`, чей `robots.txt` читается `User-Agent: *` / `Disallow: /` (перепроверено 2026-07-20). Его собственный дескриптор это признаёт и откладывает. То же решение также определяет, нуждаются ли страницы Steam `/charts/` в Playwright (строгое прочтение) или сворачиваются в простой REST-вызов к `ISteamChartsService` (прочтение как документированного API). Серьёзность **P1**, неверно **сейчас**, владелец — полоса `ingestion`. Прямо укажите, что это нуждается в *человеческом* вердикте — это вопрос интерпретации лицензии, а не технический — и что, пока на него не ответят, ничего нового не следует строить против `api.steampowered.com`.

- [ ] **Step 5: Отметьте необоснованную ступень в ADR-0014**

ADR-0014 §6 излагает лестницу эскалации `httpx → curl_cffi → playwright`, как будто все три активны. После прочёса: каждый зарегистрированный скрейпинг-источник обслуживается простым `httpx` с `render: false`; единственный обоснованный случай для **Playwright** — SPA Steam `/charts/` (заблокирован на F9); и **ни один источник в этом домене не оправдывает `curl_cffi`** — каждый кандидат, которому понадобился бы паритет по отпечаткам TLS, оказался враждебным-и-запрещённым, а не трудным-и-разрешённым.

Добавьте короткую датированную заметку на этот счёт. Не удаляйте ступень — зафиксируйте её как спекулятивную, с датой и прочёсом, который ничего не нашёл. ADR-0014 имеет `Status: Proposed`; заметка уместна, переписывание — нет.

- [ ] **Step 6: Коммит — два коммита, два репозитория**

```bash
# 1) registry repo
git -C ~/.ai/skills add .settings/de/ingestion/sources/games/
git -C ~/.ai/skills commit -m "feat(ingestion): register four FORBIDDEN games sources (2026-07-20 sweep)"

# 2) OGIP
bash src/scripts/public-hygiene.sh
git add .ai/tasks/sources-backlog.md .ai/FIXME.md docs/adr/ADR-0014-resilient-scraping-concurrency.md spec/sources/games/
git commit -o .ai/tasks/sources-backlog.md .ai/FIXME.md docs/adr/ADR-0014-resilient-scraping-concurrency.md spec/sources/games/ -F - <<'EOF'
docs(sources): record the 2026-07-20 sweep — 4 prohibitions, 1 open conflict

Epic / Kickstarter / Gamalytic all challenge-wall robots.txt itself, so no
fetch grant can be established. MobyGames signals ai-train=no with an
express Article 4 reservation plus ClaudeBot Disallow — aimed at exactly
what OGIP publishes.

F9 records the unresolved one: steam_applist is enabled on a host whose
robots.txt disallows everything. Needs a human verdict.

ADR-0014's curl_cffi rung is marked speculative: the sweep found no
permitted source in this domain that needs it.

Refs: #19
EOF
```

---

### Task 4: Наполнить глоссарий словарём домена и governance, которого ему не хватает

`.ai/AI-glossary.{en,ru}.md` держит 12 записей, все про инфраструктуру и координацию агентов. `metacritic`, `steam`, `wishlist`, `premium`, `concurrent` встречаются ноль раз. Агент, входящий в этот репозиторий, узнаёт протокол lane-lock и ничего о бизнесе, которому тот служит.

**Files:**
- Modify (via the skill, never by hand): `.ai/AI-glossary.en.md`, `.ai/AI-glossary.ru.md`

- [ ] **Step 1: Добавьте governance-термины, установленные в этой сессии**

Вызовите `/add-terms-to-glossary` (writer: `/update-terms-glossaries`). **Не** правьте файлы глоссария вручную — скилл владеет их форматом, таблицей быстрого индекса и якорными ссылками, а ручная правка десинхронизирует индекс.

Термины, каждый помечен `[project]`, с примером OGIP, который его породил:

| Term | The point |
|---|---|
| `do_not_fetch` vs `publishable` | два независимых гейта: один защищает *извлечение*, другой — переопубликацию. robots.txt — разрешение извлекать, никогда не разрешение переопубликовывать. |
| `Content-Signal: ai-train=no` | машиночитаемая оговорка прав (EU Directive 2019/790 Art. 4) — блокирует использование в ML-датасете даже там, где краулинг разрешён. MobyGames, 2026-07-20. |
| JSON-LD extraction contract | скрейпить разметку schema.org, а не видимый CSS; выбирать по `@type`, потому что страницы несут несколько блоков `ld+json`. Каждый селектор `class=*metascore*` на Metacritic совпадает с нулём узлов после пересборки. |
| `fetch_tier` escalation ladder | `httpx → curl_cffi → playwright`, эскалировать только по свидетельству; нужда в Playwright часто означает, что сайт говорит нет. |
| generated spec projection | `spec/sources/` — односторонняя проекция внерепозиторного реестра; хардлинкинг измерен небезопасным, потому что `git checkout` рвёт inode. |
| source Definition of Done | коннектор + контракт + staging-модель + запись конфига + fixture-тест + гейт дрейфа. Гейт, написанный как проза, — это гейт, который пропускают. |

- [ ] **Step 2: Добавьте термины бизнес-домена**

Они происходят из материалов Hushcrasher (сайт, пять постов рассылки, LinkedIn), прочитанных 2026-07-20. Определения — те, что даёт материал — не подставляйте общую отраслевую рамку игр.

| Term | Business definition (as given) |
|---|---|
| **scope** | Измеримые характеристики игры — время прохождения, 2D vs 3D, одиночная vs мультиплеер, жанровые теги, число платформ, озвученное аудио. Доминирующая объясняющая переменная для бюджета. |
| **Kei** | Наименьший уровень; «то, что многие назвали бы играми 'solodev'» — Undertale, Papers Please, Terraria. Медианный бюджет <$65k. |
| **Midi** | Малые и средние студии — Hades, Valheim. ≈14× Kei. |
| **AA** | «Точка входа для многомиллионных бюджетов»; сотни упомянутых в титрах людей. ≈33× Midi. |
| **AAA** | Тысячи участников. ≈10× AA. |
| **indie** | **Явно отвергнута как аналитическая категория** — смешивает эстетику, финансирование, размер команды, владение IP и творческий замысел. Свидетельство: четверть AAA-игр самоиздаются. |
| **credits length** | Число упомянутых в титрах людей, исключая special thanks и плейтестеров. Единственный сильнейший сигнал scope. |
| **PPP** | Паритет покупательной способности — сколько корзина товаров стоит локально. Наивная конвертация FX завышает цену для более бедных рынков. |
| **quantile budget estimate** | Выход — диапазон q10–q90, никогда точечная оценка: «две студии, делающие похожие игры, редко тратят одинаково». |
| **horizontal vs vertical differentiation** | Малые игры конкурируют новыми механиками (горизонтально); AA/AAA конкурируют большим объёмом контента и достоверностью (вертикально) — драйвер спирали затрат. |

**Отметьте несогласованность именования, а не сглаживайте её:** публичный сайт использует *indie / triple-I / AA / AAA*, тогда как формальная «Classification System 1.0» рассылки использует *Kei / Midi / AA / AAA*. Те же уровни, два словаря. Зафиксируйте маппинг (Kei ≈ indie/solodev, Midi ≈ triple-I) и выберите один для собственной прозы OGIP.

- [ ] **Step 3: Проверьте, что оба языка остались синхронны**

```bash
grep -c '^## ' .ai/AI-glossary.en.md .ai/AI-glossary.ru.md
```

Ожидается: равные числа, и у каждой новой EN-записи есть её RU-двойник. RU-файл — русско-сленговый двойник, а не буквальный перевод — сохраните этот регистр.

- [ ] **Step 4: Коммит**

```bash
bash src/scripts/public-hygiene.sh
git add .ai/AI-glossary.en.md .ai/AI-glossary.ru.md
git commit -o .ai/AI-glossary.en.md .ai/AI-glossary.ru.md -m "docs(glossary): source-governance + business-domain vocabulary

The glossary had 12 entries, all infra and agent coordination — nothing
about the business this platform serves.

Refs: #19"
```

---

### Task 5: Раздел документации бизнес-домена

`docs/` описывает систему полностью, а *бизнес* — вовсе никак. `docs/README.md` открывается одним предложением позиционирования и сразу переходит к архитектуре. Ничто не сообщает, на какие вопросы отвечает эта платформа или что тот или иной источник значит для аналитика.

**Files:**
- Create: `docs/domain/README.md` (бизнес-домен), `docs/domain/sources.md` (бизнес-смысл на источник)
- Modify: `docs/README.md` (строка индекса)

Жёсткое правило 8 требует `README.md` на директорию — `docs/domain/README.md` удовлетворяет ему и несёт обзор домена, поэтому отдельный индексный файл не нужен. (FIXME **F4** уже отслеживает шесть директорий-нарушителей; не добавляйте седьмую.)

- [ ] **Step 1: Исправьте рамку домена, прежде чем написать хоть слово**

Материал (hushcrasher.com, пять постов рассылки, страница компании в LinkedIn — все прочитаны 2026-07-20, все бесплатны и без пейволла) **не** поддерживает рамку, которую этот репозиторий предполагал.

Повторяющаяся ось — **production cost vs scope vs realised revenue**: во что обошлось построить, в какой уровень это ставит и что он поэтому может заработать. Ценообразование появляется как **региональные/PPP ценовые лестницы**, а не скидки. **Конверсия wishlist и кривые затухания скидок нигде в материале не появляются** — не пишите про них раздел.

Потребитель — не абстрактный «аналитик»: заявленные клиенты — **студии, издатели, инвесторы/VC и специалисты M&A**, а заявленные линейки услуг — оптимизация ценообразования, предзапусковый прогноз продаж, коммерческий due diligence и бенчмаркинг бюджета/scope.

- [ ] **Step 2: Напишите `docs/domain/README.md`**

1. **Для чего эта платформа** — четыре решения выше, на языке бизнеса, без существительных-инструментов.
2. **Кто потребитель** — студии, издатели, инвесторы, M&A; что каждый делает с датасетами.
3. **Повторяющиеся вопросы**, с собственными находками материала как иллюстрацией:
   - оценка бюджета в масштабе (≈100k тайтлов Steam, смоделированных из ≈200 раскрытых бюджетов, заявленная в пределах 10% средней погрешности);
   - декомпозиция инфляции затрат — *«игры не стали дороже делать. Мы просто делаем их больше»*;
   - насыщение рынка — медианная выручка на игру упала на 97% между 2012 и 2018;
   - конкурентное позиционирование по уровню;
   - региональная ценовая власть — *«адаптация цен к региональным экономическим реалиям — не благотворительность. Это, в первую очередь, вопрос прибыли.»*
4. **Пять измерений**, каждое со своим бизнес-вопросом и монетизированными коэффициентами материала, где он их даёт:
   - **pricing** → реализуемая ценовая лестница на рынок. Якоря уровней: Kei — несколько долларов, Midi ≈$17, AA ≈$40, AAA ≈$60.
   - **scope/length** → насколько велика эта игра в сопоставимых терминах. Удвоение времени прохождения ≈ +24% бюджета; 2D-игра ≈ на 32% дешевле своего 3D-эквивалента; мультиплеер ≈ +20%; любое озвученное аудио ≈ +70%.
   - **production budget** → сколько это должно стоить. Kei <$65k; Midi ≈14× Kei; AA ≈33× Midi; AAA ≈10× AA; издательски поддержанные тайтлы стоят в 3–4× больше самофинансируемых.
   - **traction/attention** → нашла ли она аудиторию. Материал использует **число отзывов как прокси выручки** (≈25% продаж, измеряемых долей отзывов) — это несущее использование данных о traction.
   - **quality** → двигает ли критическое восприятие коммерческие результаты. **Честно укажите, что материал едва это поддерживает**: оценки критиков практически отсутствуют в пяти постах. Измерение качества OGIP опирается на стандартную отраслевую практику, а не на это свидетельство. Отметить этот пробел ценнее, чем его замазать.
5. **Три измерения, которые материал трактует как первоклассные, а пять OGIP опускают** — назовите их как кандидатные пробелы, а не как решённый scope:
   - **team composition / headcount** — *«сильнейший предиктор бюджета — размер команды»* (2× команда ≈ +70% бюджета); соотношение управления само по себе сигнал scope (≈1 из 7 упомянутых в титрах людей в AAA);
   - **publishing model** — самоиздание vs издательская поддержка — множитель бюджета 3–4× и независимая ось сегментации;
   - **time / vintage** — каждый пост — когортное сравнение; без оси года выпуска остальные четыре измерения несопоставимы между годами.
6. **Provenance** — источники и дата, и какие утверждения принадлежат материалу, а какие — стандартной отраслевой рамке.

Исправьте одно ожидание по пути: LinkedIn был **успешно извлечён**, без стены-испытания. Он подтвердил бутиковую фирму рыночных исследований игровой индустрии, основанную в 2024, 2–10 сотрудников. Не переносите вперёд предположение, что он был нечитаем.

- [ ] **Step 3: Напишите `docs/domain/sources.md`**

Одно-два предложения на источник, на **бизнес**-языке. Технические детали относятся к `spec/sources/`; не дублируйте их. Используйте эти значения:

| Source | What an analyst uses it for |
|---|---|
| RAWG | Кросс-платформенный каталог; хребет идентичности и жанра для тайтлов, которые никогда не появляются в Steam. |
| Steam applist | Определение вселенной — знаменатель за любым утверждением о «доле релизов» или насыщении. |
| Steam appdetails | Коммерческий фактлист: цена, жанр, платформа, поддержка языков, мультиплеер. Питает scope и pricing напрямую. |
| Steam appdetails (regional) | Наблюдаемые ценовые лестницы по странам — эмпирическая проверка против PPP-справедливого ценообразования. |
| Steam appreviews | Прокси traction, замещающий проданные единицы, когда выручка не раскрыта. |
| SteamSpy | Оценки владельцев и времени игры; конвертирует внимание в грубые единицы и выручку для конкурентного сайзинга. |
| SteamCharts | Одновременность во времени: форма стартового окна и пострелизное затухание. |
| Metacritic / OpenCritic | Критическое восприятие как сигнал качества — вход в «предсказывает ли качество отзывов коммерческий результат». |
| IGDB | Структурированные метаданные: жанр, движок, франшиза, вовлечённые компании. Поставляет атрибуцию движка и студии/издателя, оба драйверы бюджета. |
| PSN Store | Консольные цены и каталог; проверяет, обобщаются ли находки Steam за пределы PC. |
| Twitch | Внимание стримеров как опережающий индикатор обнаружения и импульса стартового окна. |
| Reddit | Настроение сообщества и предрелизный интерес, дополняющие структурированные данные о traction. |

Добавьте столбец, какое из пяти измерений питает каждый источник, и отметьте, **какие источники нельзя переопубликовывать** (`publishable: false` — Metacritic, OpenCritic, SteamCharts, PSN, IGDB, Twitch, Reddit). Они питают внутренние признаки, но не могут достичь публичных датасетов. Для бизнес-читателя это продуктовое ограничение, а не сноска.

- [ ] **Step 4: Напишите раздел о пробеле покрытия — важнейшую часть этого документа**

Исследование вскрыло коллизию, которую не излагает ни один существующий документ, и она стоит больше, чем весь остальной раздел вместе взятый.

**Два самых несущих сигнала домена оба юридически недоступны OGIP.**

- **Credits length** — единственный сильнейший сигнал scope в методологии и основа предиктора размера команды (*«сильнейший предиктор бюджета — размер команды»*). Его источник — **MobyGames**, который OGIP не регистрирует и который, по прочёсу от 2026-07-20, сигнализирует `Content-Signal: ai-train=no` с явной оговоркой Article 4 плюс `User-agent: ClaudeBot / Disallow: /`.
- **Playtime** — напрямую оценённый вход в бюджет (+24% бюджета за удвоение). Его канонический источник — **HowLongToBeat**, уже зарегистрированный `do_not_fetch: true` — robots/ToS запрещают автоматическое извлечение и называют AI/ML-датасеты запрещённым использованием.

Так что **измерение production budget — ядро этого домена — сейчас не имеет разрешённого первичного входа.** Изложите это прямо, с обоими запретами по ссылкам, и зафиксируйте, что остаётся: прокси времени игры на основе Steam, IGDB `time_to_beat`, дампы Wikidata CC0 (`P2130` cost) и лицензированный или разрешительный маршрут к данным титров.

Честно отметьте одну незакрытую дверь: страница `/info/api/` MobyGames вернула 403 на автоматическое извлечение, так что условия **API** — юридически отдельные от контент-сигналов сайта — так и не были прочитаны. Человек, читающий их в браузере, мог бы это переоткрыть. Это конкретное, дешёвое следующее действие, а не тупик.

- [ ] **Step 5: Зарегистрируйте раздел в индексе документов**

Добавьте строку в таблицу в `docs/README.md`:

```markdown
| [domain/](domain/) | The business domain: what questions this platform answers, and what each source means to an analyst |
```

- [ ] **Step 6: Проверьте и закоммитьте**

```bash
bash src/scripts/public-hygiene.sh     # a public repo; the newsletter is a private company's material
bash src/scripts/check-md-refs.sh 2>/dev/null || true   # if the repo has a link checker, run it
git add docs/domain/ docs/README.md
git commit -o docs/domain/ docs/README.md -m "docs(domain): business-domain section + per-source business meaning

docs/ described the system fully and the business not at all.

Refs: #19"
```

Цитируйте скупо и атрибутируйте: рассылка — материал частной компании, а этот репозиторий публичен. Резюмируйте аналитическую рамку; не вставляйте её прозу.

---

### Task 6: Согласовать GitHub Issues с тем, что реально отгружено

**Files:** нет в репозитории — эта задача работает с `gh` и `.ai/tasks/`.

**Не запускайте полный `tasks-sync`.** Он пушит каждый грязный файл задачи, включая правки других полос в полёте. Переиспользуйте его путь `_create`/`_update` на слаг, по одному issue за раз.

- [ ] **Step 1: Закройте #18 и исправьте её scope**

[#18](https://github.com/dataengy/ogip/issues/18) — это «Resilient scraping: `ScraperSource` + landing + first scraped source». То, что отгружено, уже, чем issue: `ScraperSource`, `PoliteFetcher`, источник Metacritic и (после Задачи 1) его контракт и staging-модель. **Не** отгружено: Postgres landing, идемпотентный upsert, водяные знаки, DLQ, circuit breaker, пул парсинга.

Либо закройте #18 и откройте issue-преемник для landing/resilience-половины, либо сузьте заголовок и тело #18 до отгруженного и откройте преемника. Предпочтите первое — закрытая issue, заявляющая непостроенную работу, хуже лишней issue. Обновите `.ai/tasks/scraping-resilient.md` в соответствии с выбранным; его чеклист поставок сейчас весь неотмечен, хотя несколько сделано.

- [ ] **Step 2: Обновите #19 и очистите FIXME F6**

[#19](https://github.com/dataengy/ogip/issues/19) — это бэклог источников. FIXME **F6** фиксирует, что его тело разошлось с `.ai/tasks/sources-backlog.md`. Задача 3 меняет этот файл снова, поэтому пересинхронизируйте тело из файла задачи, а затем удалите запись F6 из `.ai/FIXME.md` — собственное правило реестра в том, что запись, ставшая неверной, удаляется, а не оставляется как археология.

- [ ] **Step 3: Откройте блокирующую issue о вердикте robots**

Заголовок: `Decide: does api.steampowered.com robots.txt govern the documented Web API?`

Тело излагает оба прочтения и что каждое подразумевает (строгое → `steam_applist` в нарушении и Steam Charts нуждается в Playwright; documented-API → `steam_applist` в порядке и Steam Charts — простой источник `dlt`), что оно блокирует любую новую работу на этом хосте и что нуждается в человеческом вердикте. Метка `p1`. Перекрёстные ссылки на F9 и #19.

- [ ] **Step 4: Откройте issue об условиях API MobyGames**

Заголовок: `Read the MobyGames API terms by hand — the budget dimension depends on it`

Сильнейший предиктор бюджета домена — длина титров, и его источник — MobyGames, чей `Content-Signal` на уровне сайта оговаривает права против ровно того, что OGIP публикует. Но **условия API так и не были прочитаны** — `/info/api/` возвращает 403 на автоматическое извлечение. Это десятиминутная человеческая задача с большой отдачей: она либо переоткрывает измерение production budget, либо окончательно его закрывает.

Тело фиксирует оба запрета (сигналы сайта MobyGames, HLTB `do_not_fetch`), заявляет, что production budget сейчас не имеет **разрешённого первичного входа**, и перечисляет запасные варианты для оценки, если API тоже закрыт: IGDB `time_to_beat`, дампы Wikidata CC0 (`P2130`), прокси времени игры на основе Steam. Метка `p1`. Перекрёстная ссылка на #19.

- [ ] **Step 5: Проверьте**

```bash
gh issue list --limit 30 --state open
gh issue view 18
```

Ожидается: #18 отражает реальность, issue-преемник существует, обе новые issue (вердикт robots, условия API MobyGames) существуют, и ни одна issue не заявляет работу, которая не отгружена.

---

## Автоматизация: что скриптовать, что переиспользовать, чего не строить

Бриф просил скиллы или — предпочтительно — скрипты, покрывающие всё вышеперечисленное. Честный ответ в том, что **большая часть этого уже автоматизирована, и оправдан лишь один новый артефакт**. Скиллы дороги в сопровождении, а в этом каталоге уже ~700; добавление одного на поток работ было бы неверным инстинктом.

| Workstream | Verdict | Why |
|---|---|---|
| Source DoD gate | **NEW: `.ci/steps/source-dod.sh` + prek hook** (Task 2) | Единственный реальный пробел. Правило, существовавшее лишь в прозе, доказуемо пропускалось. Это проверка, поэтому она должна быть кодом — и принадлежит `.ci/steps/`, чтобы CI и локальные прогоны выполняли идентичные байты. |
| Registry / forbidden entries | **Reuse** — `just sources-probe-all` · `sources-route` · `sources-drift`, and `/add-data-source` (now with Step 0 + the DoD checklist) | Уже детерминировано и уже обёрнуто в Justfile. Написание записи источника — работа суждения (оценка дословного лицензионного текста) — и не становится корректнее от того, что заскриптовано. |
| Glossary | **Reuse** — `/add-terms-to-glossary`, writer `/update-terms-glossaries` | Он уже владеет форматом файла, таблицей быстрого индекса и якорями, и у него уже есть извлечённые скрипты (`scripts/glossary_writer.py`) плюс тесты. Добавлять нечего. |
| Domain docs | **Reuse** — `/upsert-doc-about` | Разовая проза. Автоматизация документа, написанного однажды, — стоимость без отдачи. |
| GitHub Issues | **Reuse** — the per-slug `_create`/`_update` path inside `tasks-sync` | Намеренно *не* обёрнуто в новую удобную команду: полный `tasks-sync` — это опасность (он пушит грязные файлы задач других полос), а более дружелюбная обёртка сделала бы опасный путь легче достижимым. |
| Skill-copy drift | **NEW, but tiny: a `SessionStart` hook** — see below | Класс молчаливого отказа, обнаруженный в этой сессии. |

**Единственная дополнительная вещь, которую стоит построить.** `~/.claude/skills/add-data-source/skill.md` был устаревшей независимой копией, на три дня позади каталога — так что `/add-data-source` *исполнял старую версию* без симптома. `skill-sync-state` это обнаруживает, но лишь когда кто-то додумается спросить. Хук `SessionStart`, гоняющий эквивалент `just -f "$JF" status` и сообщающий только строки STALE, превращает молчаливый отказ в однострочное уведомление. Ограничьте его сообщением; хук, молча перелинковывающий файлы при старте сессии, был бы худшим багом, чем тот, что он чинит.

**О `/save-all-deterministic-for-skill-as-scripts`:** он применим к уже сделанному обновлению `/add-data-source`, и добавления там были примерами с плейсхолдерами (`<target paths>`, `<key>`), а не исполняемой логикой, так что извлекать нечего нового. Всё равно прогоните его против скилла перед следующим релизом для подтверждения — и учтите, что *существовавшие ранее* инлайновые блоки скилла вне области здесь; рефакторинг тела другого скилла не работа этого плана.

## Намеренно не в этом плане

- **Sink Postgres `landing` (ADR-0006 путь B).** Выведен из scope пользователем для этого среза; `ScraperSource` уже испускает `content_hash` как идентичность upsert, так что интерфейс готов к его возвращению.
- **Steam Charts через Playwright.** Заблокировано на вердикте robots F9. Построение до этого решения означало бы отгрузку уровня Playwright, который однострочный ответ мог бы сделать ненужным.
- **Удаление `ingestion/README.md`**, сейчас незакоммиченное в рабочем дереве. Оно принадлежит другой полосе и является нарушением жёсткого правила 8; это передача, а не работа этого плана.
