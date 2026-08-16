<!-- ru-translation-of: docs/runbooks/deploy-vps.md sha:5856dbdb5e23 -->
<!-- Автоперевод. Источник — docs/runbooks/deploy-vps.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [deploy-vps.md](deploy-vps.md)

# Runbook — Ручной деплой на VPS

- **Trigger:** выкатить новую версию на VPS. **DevOps/инфраструктура обрабатываются отдельно** ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)).
- **Owner:** сопровождающий с доступом к VPS.
- **Scripts:** [`deploy/vps/`](../../deploy/vps/README.md) — каждый принимает `--dry-run` и `--help`.

## Preconditions

- CI зелёный на деплоемом коммите.
- SSH-доступ к VPS (как `root` при первом провижининге, как сервисная учётная запись после).
- `deploy.vps.host` задан в [`config/config.yml`](../../config/config.yml) либо экспортирован `OGIP_VPS_HOST`. Он **намеренно пуст по умолчанию** — хост специфичен для оператора, поэтому ничто его не угадывает, и каждый скрипт прерывается без него.
- Секреты присутствуют на хосте в игнорируемом git-ом `.env` ([ADR-0011](../adr/ADR-0011-minimal-secrets.md)). `deploy.sh` отказывается продолжать, пока обязательный слот пуст.

## Только при первом запуске — провижининг хоста

С вашего ноутбука (управляет машиной по ssh как root; идемпотентно, безопасно перезапускать):

```bash
export OGIP_VPS_HOST=<ip-or-alias>
just vps-provision-dry     # preview every remote command
just vps-provision         # apt packages, Docker, uv, service account, checkout dir, clone
```

Затем зайдите по ssh и заполните `/opt/ogip/.env` (как минимум `RAWG_API_KEY`, `OGIP_PG_PASSWORD`).

## Шаги — деплой

```bash
just vps-deploy-dry        # preview
just vps-deploy            # deploy deploy.vps.branch (default: main)
just vps-deploy <sha>      # deploy/pin a specific commit
```

`deploy.sh` выполняется **на хосте** и делает: preflight → fetch/checkout ref → `uv sync` → рендер `.env` → проверка секретов → `prefect deploy` → `make up`. Вы точно так же можете `ssh <host>; cd /opt/ogip; deploy/vps/deploy.sh` — `just vps-deploy` это лишь ssh-мост.

Preflight прерывается **до** касания checkout-а, если отсутствует предусловие, вместо частичного деплоя. Сейчас `integrations/prefect/deploy.py` ещё не существует, поэтому настоящий деплой останавливается там по замыслу — см. [`.ai/STATUS.md`](../../.ai/STATUS.md).

## Проверка

```bash
just vps-smoke             # compose health · sample Prefect run · outputs · secret-leak scan
just vps-status            # deployed ref + containers + disk (read-only)
```

Ненулевой код выхода `vps-smoke` означает **не считать деплой удачным** — откатывайтесь.

## Откат

```bash
just vps-deploy <previous-sha>    # re-deploys that ref; detached checkout, no pull
just vps-smoke                    # confirm the rollback is healthy
```

`make down` на хосте останавливает сервисы (тома сохраняются).

## Эскалация

- Проблемы хоста/сети/провижининга/файрвола → DevOps (отдельная зона ответственности). `provision.sh` устанавливает `ufw`, но намеренно не настраивает политику портов.
