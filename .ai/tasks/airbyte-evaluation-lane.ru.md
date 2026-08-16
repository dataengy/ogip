<!-- ru-translation-of: .ai/tasks/airbyte-evaluation-lane.md sha:d95d72a69280 -->
<!-- Автоперевод. Источник — .ai/tasks/airbyte-evaluation-lane.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [airbyte-evaluation-lane.md](airbyte-evaluation-lane.md)

# Задача — Lane оценки Airbyte + Terraform (якорь: github_repos; негативный результат заложен по дизайну)

**Статус:** 🚧 в работе · **Приоритет:** P3 (бэклог) · **Issue:** [#41](https://github.com/dataengy/ogip/issues/41)

Lane: `airbyte` (перед записью захватите `obj--airbyte`). Всё живёт в
`experimental/ingestion/airbyte/` — **вне пути `make`**. SSoT дизайна:
[`docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`](../../docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md) ·
план: [`docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md`](../../docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md) ·
техдолг: [`docs/techdebt/airbyte-lane.md`](../../docs/techdebt/airbyte-lane.md).

## Что это

**Оценка** Airbyte + Terraform на его единственном лучшем кейсе — **не** продакшен-инжест.
Перечитывание домена (cost × scope × revenue) не нашло **ни одного** managed-коннектора,
подходящего под источники продукта; продуктовый инжест остаётся на **dlt**. Результат:
*измеренное* сравнение трёх вариантов Terraform-драйвера (yamldecode / codegen-`.tf` /
codegen-`.tfvars`) поверх одного общего `modules/airbyte-connection`, плюс честный вердикт.

## Якорный источник

`github_repos` через `airbyte/source-github` 2.1.37 — единственный коннектор в OSS-реестре из
591 источника, который сертифицирован, **и** является настоящим кодом, **и** работает с
публичными данными. `source-twitch` не существует (→ собственный declarative-коннектор);
`source-reddit` — community/manifest-only (контрпример).
Сравнение: [`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`](../../docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md).

## Чек-лист

- [x] Дизайн-спека, план реализации, трекер техдолга, документ сравнения
- [x] `airbyte_emit.py validate` — настоящий, зелёный против живого реестра; проверен на негативных кейсах
- [x] Pre-commit-гейт `src/scripts/airbyte-blocks-check.sh`
- [x] Фаза 0 — worktree `lane/airbyte`; `services.airbyte_port` + `postgres.airbyte_schema`
      в конфиг-SSoT; каркас `experimental/ingestion/airbyte/`
- [x] Скрипты Фазы 1 (`up`/`down`/`credentials.sh` + Justfile) — **runtime NO-GO на этой
      машине**, см. техдолг (abctl исчерпал диск посреди установки; предпосылка не проверена)
- [x] Фаза 2 — общий `modules/airbyte-connection`, провайдер 1.2.0, схема проверена, validate зелёный
- [~] Фаза 3 — Вариант A (yamldecode `for_each`): HCL **validate-зелёный офлайн** и доказанно в консоли
      обнаруживает github_repos+reddit_posts, собирает 6 стримов github, парсит репозиторий из
      url дескриптора. `plan`/`apply` (тот самый *измеряемый* датапоинт) заблокированы на runtime.
- [ ] Фаза 4 — Варианты B и C; убирает заглушку `render`; drift-гейт
- [ ] Фаза 5 — Declarative-коннектор для Twitch
- [x] Фаза 6 — CI-джоба `airbyte-tf` (`fmt`+`validate`; `plan`/`apply` — никогда: нет доступного API)
- [ ] Фаза 7 — доделать деплой `/add-airbyte-sync`; README с **измеренным** вердиктом

## Гейты, которые кусаются

- **abctl требует ≥10 GiB свободного места** (k8s-in-docker). Перепроверить перед Фазой 1.
- Фаза 1 — настоящий go/no-go: если abctl + провайдер 1.2.0 не договорятся, runtime-предпосылка
  рушится — озвучьте это явно, **не** откатывайтесь на удалённый compose-v0.63.
- `airbyte_emit.py render <a|b|c>` — **громкая заглушка (exit 2)**, пока не существует TF-модуль —
  принцип «откладывай, а не имитируй» (defer-don't-fake), отслеживается в техдолге, никогда не
  молчаливый no-op.

<!-- ogip-task: airbyte-evaluation-lane -->
