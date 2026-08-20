<!-- ru-translation-of: docs/techdebt/stale-branches.md sha:d95918beb47d -->
<!-- Автоперевод. Источник — docs/techdebt/stale-branches.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [stale-branches.md](stale-branches.md)

# Реестр stale-веток (директива владельца 2026-07-30: помечать, никогда не удалять)

Ветки, чья работа полностью содержится в `dev` (или вытеснена более новой). Они **сохранены
как указатели** — не разрабатывайте на них, не перебазируйте их, не удаляйте их. Прежде чем
доверять, проверяйте вхождение: `git rev-list --left-right --count origin/dev...<branch>`
(ahead 0 = содержится).

| Ветка | Tip | Состояние | Влито через |
|---|---|---|---|
| `lane/reroot-dbt-bruin-primary` | `2d3b9da` | stale — влита | PR #46 (re-root T1–T9, ADR-0020) |
| `lane/neighbour-salvage` | `b32c3e2` | stale — влита | PR #45 (паритет фикстур ODTS + ru-gitignore) |
| `lane/core-pipeline` | `90383ec` | stale — содержится | влита в dev до финализации |
| `lane/transform-dq-expansion` | `452ad8c` | stale — содержится | влита в dev до финализации |
| `lane/airbyte` | `5d67276` | stale — содержится (== старый tip dev) | оценочный lane, рантайм NO-GO (#41) |
| `lane/evidence` · `lane/obs` · `lane/s3` · `lane/vps` | `1b9071d` | stale — пустые заглушки (отставание 138+), без уникальной работы | никогда не разрабатывались |
| `lane/dagster` | `645d190` | stale — влита 2026-07-30 | PR #34 (уплощённые defs, разделение warehouse, dbt-нативный DQ) |
| `lane/odos-compiler` | `6669142` | stale — влита 2026-07-30 (адаптеры/эквивалентность остаются открытыми в #37) | PR #49 |

Историческая справка: 2026-07-30 (шаг 18 финализации) эти указатели были ненадолго удалены
после доказательства вхождения, а затем в тот же день восстановлены ровно на своих tip,
когда владелец установил политику «помечать, не удалять». Ни один коммит не был потерян.
Замороженные *фичи* живут в [finalization-tbd.md](finalization-tbd.md) — громкие заглушки +
issues, никогда — тихое удаление.
