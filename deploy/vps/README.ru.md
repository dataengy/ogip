<!-- ru-translation-of: deploy/vps/README.md sha:cca5242f952e -->
<!-- Автоперевод. Источник — deploy/vps/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `deploy/vps/` — ручной деплой на VPS

Скрипты, стоящие за [`docs/runbooks/deploy-vps.md`](../../docs/runbooks/deploy-vps.md).
Деплой **ручной и ведётся по runbook**; инфраструктура/DevOps принадлежит отдельному владельцу
([ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md)). Без k8s, без Terraform.

## Скрипты

| Скрипт | Где выполняется | Назначение |
|---|---|---|
| `lib.sh` | — | Общие хелперы: разрешение настроек, обёртки над `ssh`, dry-run, логирование. Подключается через source, не запускается. |
| `provision.sh` | **ваш ноутбук** (управляет хостом от root) | Первичный bootstrap: apt-пакеты, Docker, uv, сервисный аккаунт, каталог чекаута, первый clone. Идемпотентен. |
| `deploy.sh` | **VPS** | Fetch/checkout ref → `uv sync` → рендер `.env` → проверка секретов → `prefect deploy` → `make up`. Идемпотентен. |
| `check-secrets.sh` | **VPS** | Падает, если обязательный слот секрета в `.env` пуст. Вызывается из `deploy.sh`; никогда не печатает значения. |
| `smoke.sh` | **VPS** | Верификация после деплоя: здоровье compose, пробный запуск Prefect, выходные данные, скан на утечку секретов. |

Каждый скрипт принимает `--dry-run` (печатать команды, ничего не менять) и `--help`.

## Настройки

Разрешаются в `lib.sh` из `config/config.yml → deploy.vps.*` — SSoT
([AGENTS.md](../../.ai/AGENTS.md), правило 3). Каждый ключ можно переопределить env-переменной `OGIP_VPS_*`:

| Настройка | Env-переопределение | По умолчанию | Примечания |
|---|---|---|---|
| `host` | `OGIP_VPS_HOST` | _(пусто)_ | IP / hostname / алиас из `ssh_config`. **Пусто намеренно** — специфично для оператора, никогда не коммитится. |
| `user` | `OGIP_VPS_USER` | `ogip` | Непривилегированный сервисный аккаунт, создаваемый `provision.sh`. |
| `port` | `OGIP_VPS_PORT` | `22` | Порт ssh. |
| `path` | `OGIP_VPS_PATH` | `/opt/ogip` | Расположение чекаута на хосте. |
| `branch` | `OGIP_VPS_BRANCH` | `main` | Git-ref для деплоя. |
| `repo_url` | `OGIP_VPS_REPO_URL` | `github.com/dataengy/ogip` | URL для clone. |

Отсутствующая или пустая настройка **прерывает выполнение** с именем ключа и обоими местами,
откуда она могла бы взяться, — здесь ничто не откатывается к догадке, потому что хост
«по умолчанию» — это ровно то, как деплоят не на ту машину.

Эти значения читаются напрямую из `config.yml` через `yq` и намеренно **не** рендерятся
в `.env`: хост специфичен для оператора, а `.env` — для приложения, а не для способа
добраться до машины.

## Использование

```bash
export OGIP_VPS_HOST=203.0.113.10       # or set deploy.vps.host in config/config.yml

just vps-provision-dry                  # preview the bootstrap
just vps-provision                      # bootstrap the box (once)

# fill secrets on the host: ssh in, edit /opt/ogip/.env  (ADR-0011: gitignored .env)

just vps-deploy-preview                 # host-free: validate deploy logic + preflight (no ssh)
just vps-deploy-dry                     # on-host preview (needs a reachable host)
just vps-deploy                         # deploy deploy.vps.branch
just vps-deploy abc1234                 # deploy/roll back to a specific sha
just vps-smoke                          # verify
just vps-status                         # containers + current ref
```

## Запуск в прод на Hetzner CX32

Рекомендуемая цель: **Hetzner CX32** (4 vCPU / 8 GB / 80 GB NVMe, ~€7/мес) + **Cloudflare R2**
для lake (нулевой egress). Ubuntu 24.04 LTS. Доступные извне UI остаются закрытыми — к
Prefect/Grafana ходите через SSH-туннель, а не через публичный порт (ADR-0012).

```bash
# 1. On Hetzner: create a CX32, image Ubuntu 24.04, add YOUR ssh key. Note the IP.
# 2. Point the tooling at it (never committed — operator-specific):
export OGIP_VPS_HOST=<the-ip>

# 3. Bootstrap once (idempotent: safe to re-run), then fill secrets on the box:
just vps-provision
ssh ogip@$OGIP_VPS_HOST 'nano /opt/ogip/.env'   # RAWG_API_KEY, R2 creds — ADR-0011

# 4. Deploy + verify:
just vps-deploy
just vps-smoke
```

Добавьте `+2–4 GB swap` (пики DuckDB всплесковые) и только `ufw allow 22`. Карта, выпущенная
в России? Hetzner её отклонит — используйте **Timeweb Cloud** или **Selectel**
(4 vCPU/8 GB ≈ 700–1200 ₽/мес); `provision.sh` не привязан к хостеру (обычный Ubuntu),
так что больше ничего не меняется.

## Известные пробелы (блокируют реальный деплой)

`deploy.sh` выполняет **preflight** и отказывается стартовать, пока не существует
перечисленное ниже — отслеживается в [`.ai/STATUS.md`](../../.ai/STATUS.md):

- `integrations/prefect/deploy.py` — на него ссылается `just prefect-deploy`; **ещё не
  написан** (lane core-pipeline). Это **единственный** оставшийся блокер; см. handoff в
  STATUS.md о решении по модели запуска Prefect, которое он несёт.
- ~~`deploy/docker-compose.yml`~~ — **готов**, приехал с lane compose/obs (2026-07-17).

Пока `deploy.py` не появится, `provision.sh` работает от начала до конца, а `deploy.sh` чисто
останавливается на preflight вместо того, чтобы задеплоить наполовину.
