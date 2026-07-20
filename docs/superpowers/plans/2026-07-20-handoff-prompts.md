# Handoff-промпты — сессия `3ad45e75` (OGIP @ dev)

Fan-out оставшейся работы: 6 промптов для 6 разных приёмников. Каждый несёт четыре обязательных
элемента — где живёт работа · что уже установлено (не выводить заново) · конкретный следующий шаг ·
ловушка, в которую эта сессия уже попала.

Источник: `/handoff-prompts` (`agentic/session/`). Лимит `max_prompts: 6` — достигнут ровно.

---

## 1 → Сессия в каталоге скиллов (`~/.ai/skills/`) — Wave 1

```
Создай три скилла Wave 1 из proposal-документа
/Users/nk.myg/gi/@dataengy/OGIP/docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md
(раздел «Wave 1»): describe-source-business-value и design-source-pipeline в de/ingestion,
generate-synthetic-fixtures в новой области de/testing.

Уже установлено — не перепроверяй: аудит всех 521 скиллов каталога уже проведён, у этих трёх
покрытие НУЛЕВОЕ (grep по 'synthetic data|fixture generat|mock data|faker' даёт 0 совпадений).
ODCS-скилл создавать НЕ надо — /generate-odcs-specs в de/contracts/ уже покрывает это целиком.
Границу извлечения задаёт /find-sources-and-match-tool: он уже владеет Шагами 0–2 родителя
(research + probe + route), твои скиллы начинаются ПОСЛЕ роутинга.

Следующий шаг: сначала /propose-skill-for-that, дождись гейта, и только потом /create-skill на
каждый. Скилл-файлы никогда не пишутся руками — это стоячая политика. После каждого создания
обязателен /save-all-deterministic-for-skill-as-scripts <slug>, затем skill-sync-state.

Ловушка этой сессии: `~/.claude/skills/<slug>/skill.md` может оказаться НЕ хардлинком, а
самостоятельной устаревшей копией. У add-data-source она отстала на 3 дня и 6 КБ — то есть
/add-data-source молча исполнял старую версию, без единого симптома. `deploy-skill` обновляет
только symlink-цели; чинит именно `hardlink-skill-files <catalog-dir> <target-dir>`. Проверяй
sync-state ПОСЛЕ каждой правки, а не в конце.
```

## 2 → Сессия в каталоге скиллов — Wave 2 (после Wave 1)

```
Создай пять implementer-скиллов Wave 2 по документу
/Users/nk.myg/gi/@dataengy/OGIP/docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md:
write-ingestion-dlt / -ingestr / -airbyte-oss / -scraping / -complex-api в de/ingestion.

Уже установлено: разрез НЕ произвольный — он повторяет словарь роутера
`~/.ai/skills/.settings/de/ingestion/tool_routing.yml` (8 вердиктов). Скиллы нужны только под
пять «живых»; spark и gcp зарезервированы без прецедентов в реестре, none означает FORBIDDEN —
под эти три скиллы не создавать.

Следующий шаг и разрешение НЕ кодить: запрос заказчика был «5 отдельных скиллов под dlt»
(native / standalone / Dagster / OpenDBT / Prefect). Документ рекомендует ОТКАЗАТЬ и сделать один
write-ingestion-dlt с секцией «где это выполняется», делегирующей по имени в уже существующие
/add-dagster-module, /integrate-sql-tool-with-prefect, /call-dagster-from-prefect. Прочитай
аргумент в разделе «The one place the literal ask should be refused» и реши сам; если сочтёшь
разбиение оправданным — напиши почему, но не реализуй молча ни один из вариантов.

Ловушка: общие законы (Layer-0, SSoT-config, fixture-size/LFS) должны ОСТАТЬСЯ в родителе и
цитироваться по ссылке. Скопировать их в пять скиллов — это ровно тот guardrail, который
/split-skill-on-subskills запрещает: «do not leave provider-specific logic duplicated».
```

## 3 → Сессия OGIP (lane `ingestion`) — долг Metacritic + гейт DoD

```
Выполни Задачи 1 и 2 из плана
docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md в репозитории
/Users/nk.myg/gi/@dataengy/OGIP: ODCS-контракт spec/contracts/metacritic/metacritic__game.odcs.yaml
+ staging-модель spec/sql/staging/stg_metacritic__game.sql, затем исполняемый гейт
.ci/steps/source-dod.sh с тестом src/tests/unit/test_source_dod_check.py.

Уже установлено — не выводить заново: коннектор ingestion/sources/metacritic.py (95 строк) УЖЕ
существует и уже приземляет raw/metacritic__game Parquet, коммит dc02ddb. Отсутствуют ровно
контракт и staging-модель. Полный YAML контракта и полный SQL модели приведены в плане дословно —
это транскрипция, а не проектирование. Freshness SLA = 7d, не 1d как у RAWG (агрегат критиков
статичен). Гейты в этом репозитории ходят ТОЛЬКО через .ci/run.sh <step> → .ci/steps/<step>.sh;
корневого .pre-commit-config.yaml нет, он лежит в config/.

Следующий шаг: сначала прочитай реальную форму приземлённого Parquet и пиши контракт под неё —
не под то, что обещает `_record()` в коннекторе.

Ловушка: гейт source-dod.sh по построению КРАСНЫЙ до тех пор, пока Задача 1 не сделана. Это не
баг — в этом его смысл. Не «чини» его послаблением проверки. И прогони /verify-gate-actually-covers
прежде чем поверить в зелёный: гейт, который не матчит ни одного файла, выглядит точно как успех.
```

## 4 → Сессия OGIP (lane `docs`) — реестр, глоссарий, бизнес-домен

```
Выполни Задачи 3, 4 и 5 из плана
docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md
(/Users/nk.myg/gi/@dataengy/OGIP): четыре FORBIDDEN-записи в реестр, термины в глоссарий,
новый раздел docs/domain/.

Уже установлено: домен клиента — это себестоимость × скоуп × выручка, НЕ скидки и НЕ конверсия
вишлистов. Wishlist-конверсия и кривые дисконта не встречаются в материале ни разу; раздел про них
писать нельзя. Словарь тиров — Kei / Midi / AA / AAA. LinkedIn-страница компании ЧИТАЕТСЯ без
403 — предыдущее предположение о блокировке было неверным, не тащи его дальше. Реестр источников
живёт ВНЕ репозитория, в ~/.ai/skills/.settings/de/ingestion/sources/<area>/<key>.yml;
spec/sources/*.yaml — односторонняя генерируемая проекция, править её напрямую бессмысленно.

Следующий шаг: глоссарий пополнять только через /add-terms-to-glossary, руками — никогда.
Это два коммита в двух разных репозиториях.

Ловушка: измерение «производственный бюджет» не имеет ни одного разрешённого источника — MobyGames
(credits length) и HowLongToBeat (playtime) заблокированы оба. Напиши это в docs/domain/ как явный
пробел покрытия. Соблазн замазать его правдоподобной формулировкой очень велик и создаст документ,
который врёт о возможностях платформы.
```

## 5 → Человеку (не сессии) — два юридических блокера

```
Два вопроса требуют человеческого чтения в браузере; агент их закрыть не может.

(1) MobyGames — условия API. Страница https://www.mobygames.com/info/api/ отдаёт 403 ботам, то есть
её условия НИКТО не читал. Юридически они отдельны от сигналов сайта (Content-Signal: ai-train=no,
оговорка по ст. 4 Директивы ЕС 2019/790, ClaudeBot Disallow: /). Открой в браузере и прочти: если
API-лицензия допускает производные датасеты, к OGIP возвращается измерение производственного
бюджета — сильнейший сигнал всей методологии домена. Десять минут чтения против целого измерения
модели: лучшее соотношение усилия к результату во всём бэклоге.

(2) api.steampowered.com — трактовка robots.txt. Файл отдаёт `User-Agent: * / Disallow: /`, при
этом источник steam_applist зарегистрирован как publishable: true, tier: direct, routing → dlt
именно на этом хосте. Строгое чтение → источник в нарушении и Steam Charts требует Playwright;
чтение «robots не покрывает документированный API» → всё в порядке и Steam Charts сводится к
обычному dlt. Это лицензионное суждение, а не техническая проверка — оно за человеком. Пока
вердикта нет, вся новая работа по этому хосту заблокирована; зафиксировано как FIXME F9.
```

## 6 → Сессия в каталоге скиллов — Wave 3 (последней)

```
После того как Wave 1 и Wave 2 созданы и синхронизированы: сделай Wave 3 из
docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md — скилл
author-pipeline-stage-tests (de/testing) и цепочечный onboard-data-source (de/ingestion), затем
отрефактори родителя /add-data-source под делегирование.

Уже установлено: родитель НЕ удаляется и не превращается в зонтик. За ним остаются preconditions
(lane lock), Шаг 0 (already built?), Шаг 3 (гейт легальности — блокирующий, его двигать нельзя),
три закона и Definition of Done, Шаг 6 (ship). Всё остальное делегируется по имени. Файл сейчас
243 строки: ~/.ai/skills/_catalog/de/ingestion/add-data-source/SKILL.md.

Следующий шаг: Wave 3 обязана идти ПОСЛЕ Wave 1–2. Оркестрирующий скилл, называющий ещё не
существующие скиллы, — это сломанный скилл, который читается как рабочий. Проверь наличие каждого
делегата через `just -f ~/.ai/skills/_scripts/skills/management/Justfile skill-locate <slug>`
прежде чем сослаться на него.

Ловушка: правка родителя идёт только через /upsert-skill, и после неё обязателен
validate-skill <slug> — у него лимит description ≤1024 символов одной строкой, а описание
add-data-source уже длинное и при добавлении делегатов легко его пробить.
```

---

## Не вошло в fan-out

- **Незакоммиченное в OGIP**: `.claude/agents/ogip-ingestion-engineer.md` (новый),
  `.claude/agents/ogip-lane-worker.md` (§0.5), два плановых документа. Плюс правки каталога
  скиллов — отдельный репозиторий, отдельный коммит.
- **Удерживается лок** `obj--agents-skills` (STALE, 3.4 ч).
- **Не проверено**: сколько ещё скиллов каталога имеют ту же drift-проблему устаревших копий в
  `~/.claude/skills/`. Одна найдена; выборка из одного.
