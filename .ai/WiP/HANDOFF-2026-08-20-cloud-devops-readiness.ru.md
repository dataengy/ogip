<!-- ru-translation-of: .ai/WiP/HANDOFF-2026-08-20-cloud-devops-readiness.md sha:a1061f3a053d -->
<!-- Автоперевод. Источник — .ai/WiP/HANDOFF-2026-08-20-cloud-devops-readiness.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [HANDOFF-2026-08-20-cloud-devops-readiness.md](HANDOFF-2026-08-20-cloud-devops-readiness.md)

# ХЭНДОФФ / снимок перед компакцией — готовность cloud-devops (2026-08-20)

Рамки сессии: [#53](https://github.com/dataengy/ogip/issues/53) — роль cloud-devops,
verify-скиллы, аудит готовности, предложение деплоя.

## Открытые задачи с ключами

- [#53](https://github.com/dataengy/ogip/issues/53) — готовность cloud-devops:
  **результаты отгружены**; остаётся открытой, пока не принято решение по предложению
  деплоя и первый деплой не занесён в журнал готовности
  [tasks/cloud-devops-readiness.md](../tasks/cloud-devops-readiness.md).
- [#54](https://github.com/dataengy/ogip/issues/54) — красный e2e в dev CI (кейс
  `[bruin]`) под незапиненным свежайшим Bruin CLI в CI. **Хэндофф в lane `core-pipeline`**
  (владеет `.ci/` + workflows): запинить версию в `.github/workflows/ci.yml`. Продвижение
  dev→main заблокировано до исправления.
- [#52](https://github.com/dataengy/ogip/issues/52) — человеческие шаги эскроу секретов
  всё ещё не выполнены: git-secret `initialized=NO`, блоба нет; слоты `OGIP_PG_PASSWORD`,
  `RAWG_API_KEY`.

## Сделано, с SHA коммитов (всё на `dev`, запушено)

- `85ca791` feat(config): `config/verify.yml` — 16-стадийная матрица верификации
  local+cloud.
- `bc4cf5c` chore(ai): `.claude/agents/ogip-cloud-devops.md` (ролевой агент,
  зарегистрирован), `.ai/tasks/cloud-devops-readiness.md`, строки in-use в `.ai/SKILLS.md`.
- `d3fce67` chore(ai): зафиксирована находка #54.
- `a3c3e39` chore(ai): зафиксировано одобрение скиллов на review-гейте.
- Каталог скиллов (`~/.ai/skills/_catalog/infra/project-readiness/`):
  `verify-project-local-full` · `verify-project-cloud-deployable` ·
  `propose-project-deploy` (только slash) + раннер
  `~/.ai/skills/_scripts/infra/project-readiness/{verify-stages.sh,Justfile}`.
  **Одобрены 2026-08-16 и задеплоены**: захардлинканы в `~/.claude/skills` (проверено по
  inode), проштампованы провенансом, синхронизированы claude→codex, строки в INDEX
  добавлены.
- Первый прогон готовности (2026-08-16): **LOCAL-VERIFIED** (e2e-прогон Prefect, 10/10
  DQ-мониторов, артефакты `.run/data/outputs/*.parquet`) ·
  **DEPLOYABLE-WITH-OPERATOR-INPUT** (хост + эскроу — единственные блокеры). Итоговый
  комментарий: #53.

## Нерешённое, с причиной

- **Предложение деплоя ждёт решения владельца** — main → VPS класса Hetzner согласно
  ADR-0012; агент не вправе деплоить без явного одобрения. Шаги — в
  [tasks/cloud-devops-readiness.md](../tasks/cloud-devops-readiness.md) + комментарий #53.
- **Коммит в репозиторий скиллов**: добавления каталога/раннера/INDEX лежат на диске, но
  НЕ ЗАКОММИЧЕНЫ в `~/.ai/skills` (тот репозиторий ведёт владелец, и он уже был грязным на
  1244 файла — коммит замёл бы чужую работу). Риск: `git clean` там их уничтожит.
- **Хэндофф structure-validate** (в файле задачи #53): `.ci/steps/structure-validate.sh`
  считает файлы, попавшие под gitignore; стадия помечена `optional: true` в матрице, пока
  core-pipeline её не починит.
- Существовавший ранее флаг хука docs-check «1 doc missing/stale RU» — появился до этой
  сессии, здесь не разбирался.

## Принятые решения (не пересматривать)

- Семейство скиллов живёт в домене каталога `infra/project-readiness`; тир классификатора =
  default/normal (не heavy).
- `propose-project-deploy` — только slash (`disable-model-invocation: true`); деплои всегда
  проходят через человека (ADR-0012).
- Пути e2e-доказательств используют `platform.data_dir` (`.run/data/outputs/`), а НЕ
  `outputs/`.
- Принцип CI-паритета: стадии матрицы зеркалят `.ci/steps/*`; пустой `OGIP_VPS_HOST` ⇒
  NEEDS-OPERATOR, так задумано.
- Lane `cloud-devops` = `config/verify.yml` + файл агента + файл задачи; `deploy/vps/`
  остаётся за `core-pipeline` (#17).

## Возобновление

```bash
just -f ~/.ai/skills/_scripts/infra/project-readiness/Justfile verify local   # re-baseline
just -f ~/.ai/skills/_scripts/infra/project-readiness/Justfile verify cloud
```
