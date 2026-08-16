<!-- ru-translation-of: .ai/tasks/cloud-devops-readiness.md sha:caf27eea058a -->
<!-- Автоперевод. Источник — .ai/tasks/cloud-devops-readiness.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [cloud-devops-readiness.md](cloud-devops-readiness.md)

# Задача — готовность cloud-devops ([#53](https://github.com/dataengy/ogip/issues/53))

**Роль:** [`.claude/agents/ogip-cloud-devops.md`](../../.claude/agents/ogip-cloud-devops.md) ·
**Матрица:** [`config/verify.yml`](../../config/verify.yml) ·
**Lane:** `cloud-devops` (этот файл, файл агента, матрица; `deploy/vps/` остаётся за
`core-pipeline` / [#17](https://github.com/dataengy/ogip/issues/17))

Доказать, что OGIP работает **полностью локально**, доказать, что его можно **полностью
задеплоить + запустить + верифицировать вне рабочей станции** (ручной VPS,
[ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md)), заапсертить всё, что для
этого требуется, и держать перед владельцем актуальное **предложение о деплое** — сами деплои
всегда утверждает человек.

## Как запускать

```bash
JF=~/.ai/skills/_scripts/infra/project-readiness/Justfile   # skills-catalog runner
just -f "$JF" verify local    # whole-project local verification (CI-parity stages)
just -f "$JF" verify cloud    # deployability: assets, runbooks, CI, escrow, vps dry-runs
```

Семейство скиллов (каталог `infra/project-readiness`): `/verify-project-local-full` →
`/verify-project-cloud-deployable` → `/propose-project-deploy` (только slash, человеческий гейт).

## Статус

- [x] Матрица верификации (`config/verify.yml`) — local (8 стадий) + cloud (8 стадий)
- [x] Семейство скиллов создано в каталоге + раннер стадий (`verify-stages.sh`)
- [x] Ролевой агент `ogip-cloud-devops`
- [x] Скиллы одобрены на review-гейте → развёрнуты в `~/.claude/skills` + синхронизированы с
      остальными агентными таргетами (2026-08-16, хардлинки проверены по inode; провенанс проставлен)
- [x] Первый полный прогон готовности записан ниже
- [ ] Предложение о деплое одобрено / отклонено владельцем

## Журнал готовности

| дата | вердикт local | вердикт cloud | заметки |
|---|---|---|---|
| 2026-08-16 | **LOCAL-VERIFIED** (6 PASS · 2 WARN) | **DEPLOYABLE-WITH-OPERATOR-INPUT** (5 PASS · 3 NEEDS-OPERATOR) | e2e прогнал Prefect-джобу, 10/10 DQ-мониторов зелёные, артефакты в `.run/data/outputs/`; CI зелёный на `dev`. WARN'ы: obs-stack (docker-демон на этом хосте не запущен), structure-validate (см. handoff). Ввод оператора: `OGIP_VPS_HOST` + эскроу секретов. |

## Находки / handoff'ы

1. **Handoff → lane `core-pipeline`** (владелец `.ci/`): `.ci/steps/structure-validate.sh`
   считает **gitignored**-файлы, поэтому санкционированные локальные переводы `*.ru.md`
   (`AGENTS.ru.md`, `README.ru.md`) валят его локально, тогда как чистый чекаут CI проходит.
   Фикс: перечислять через `git ls-files --others --exclude-standard` (+tracked) вместо голого
   `ls`. До тех пор матрица держит эту стадию как `optional`.
2. **Эскроу секретов не выполнен** (человеческие шаги, [#52](https://github.com/dataengy/ogip/issues/52)):
   `just secrets-doctor` сообщает, что бэкенды здоровы, но git-secret `initialized=NO`, нет
   блоба `.env.secrets.secret`. Обязательные слоты для деплоя: `OGIP_PG_PASSWORD`,
   `RAWG_API_KEY` (`deploy/vps/check-secrets.sh`). Эскроу перед любым VPS-деплоем:
   `just secrets-setup-git-secret && just secrets-hide` (нужен GPG-ключ) **или** `bw unlock` +
   `just secrets-push`.
3. **e2e в CI на dev красный — дрейф Bruin CLI** ([#54](https://github.com/dataengy/ogip/issues/54),
   handoff → `core-pipeline`): CI ставит незапиненный последний Bruin; e2e-кейс `[bruin]` там
   падает, тогда как локальная v0.11.680 зелёная. Блокирует промоушен dev→main (не деплой
   `main` — CI `main` зелёный). Фикс: запинить версию CLI в `.github/workflows/ci.yml`. До тех
   пор облачная стадия `ci-green-dev` честно падает.
