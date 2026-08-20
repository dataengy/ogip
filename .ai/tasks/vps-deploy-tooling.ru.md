<!-- ru-translation-of: .ai/tasks/vps-deploy-tooling.md sha:975eee2957f2 -->
<!-- Автоперевод. Источник — .ai/tasks/vps-deploy-tooling.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [vps-deploy-tooling.md](vps-deploy-tooling.md)

# Задача — инструментарий VPS-деплоя (`deploy/vps/`)

**Статус:** 🚧 в работе — скрипты написаны, отлинчены и проверены в dry-run; реальный деплой на хост —
скоуп V2 (финализация 2026-07-30): `integrations/prefect/{deploy,trigger}.py` существуют как громкие
TBD-заглушки (exit 2, docs/techdebt/finalization-tbd.md, строка 6), условие разблокировки не изменилось
(закреплённая модель запуска воплощена + реальный хост) — см. [#17](https://github.com/dataengy/ogip/issues/17).

Lane: `vps` (объект блокировки параллельных сессий). Область: `deploy/vps/`, рецепты Justfile `vps-*`
и `config/config.yml → deploy.vps.*`. Запись решения:
[ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md) · ранбук:
[deploy-vps.md](../../docs/runbooks/deploy-vps.md).

## Зачем

`docs/runbooks/deploy-vps.md` пошагово документировал `deploy/vps/deploy.sh`, и ADR-0012
его принял — но скрипт так и не был написан. Ранбук описывал несуществующий скрипт.

## Сделано

- `deploy/vps/lib.sh` — разрешение настроек (SSoT конфига + переопределения `OGIP_VPS_*`), ssh-обёртки,
  dry-run, громкое логирование сбоев.
- `deploy/vps/provision.sh` — бутстрап голого хоста по ssh (apt, Docker, uv, сервисный аккаунт,
  каталог чекаута, первый клон). Идемпотентен.
- `deploy/vps/deploy.sh` — выполняется на хосте: fetch/checkout ссылки (ref) → `uv sync` → рендер `.env` →
  проверка секретов → `prefect deploy` → `make up`. Позиционный ref закрепляет sha для отката.
- `deploy/vps/check-secrets.sh` — блокирует деплой, если обязательный слот `.env` пуст; никогда
  не печатает значение.
- `deploy/vps/smoke.sh` — проверка после деплоя (здоровье compose, запуск Prefect, выходные данные,
  скан на утечку секретов).
- `deploy/vps/remote.sh` · `status.sh` — управляют хостовыми скриптами с ноутбука; статус только на чтение.
- Justfile: `vps-provision[-dry]` · `vps-deploy[-dry]` · `vps-smoke` · `vps-status`.
- `src/scripts/tasks_sync.py` — `.ai/tasks/*.md` → GitHub Issues (рецепт `just tasks-sync`
  указывал на `integrations/github/tasks_sync.py`, который так и не был написан).

## Проверено

- `.ci/run.sh bash-lint` зелёный (shellcheck + shfmt, 21 файл); ruff + pyright strict чистые.
- `provision.sh --dry-run` печатает полный план удалённых действий, не открывая соединения.
- Незаданный хост прерывает работу с понятным сообщением, называющим ключ и оба источника.
- `deploy.sh --dry-run` останавливается на префлайте вместо полудеплоя.
- `tasks_sync.py --dry-run` ничего не создаёт (проверено на живом трекере).

## Заметки по дизайну

- **Никаких дефолтов для настроек.** Пустой хост прерывает работу. Хост по умолчанию — верный способ
  задеплоить не на ту машину.
- **Префлайт вместо частичного деплоя.** `deploy.sh` отказывается стартовать при отсутствии
  предусловия, вместо того чтобы сделать fetch + sync и умереть на шаге 5.
- **Настройки не рендерятся в `.env`.** Хост индивидуален для оператора; `.env` — для приложения,
  а не для того, как мы добираемся до машины. `lib.sh` читает `config.yml` через `yq`, поэтому
  конкурентно правимый `config/.env-render.py` менять не пришлось.

## Заблокировано (другие lane)

Реальный деплой не может пройти, пока не существуют вот эти вещи — префлайт `deploy.sh` называет обе:

- `integrations/prefect/deploy.py` — `just prefect-deploy` (lane core-pipeline).
- `deploy/docker-compose.yml` — `make up` (приземлён 2026-07-17 силами lane obs/compose).

## Дальнейшие шаги

- Направить `deploy.vps.host` на реальную машину и прогнать `provision → deploy → smoke` от начала до конца.
- `deploy.vps.compose_profiles` объявлен, но пока не потребляется `deploy.sh` (`make up` поднимает
  только базовые сервисы) — подключить, когда obs-стек тоже должен подниматься на хосте.
- Политика файрвола/портов намеренно не настроена: по ADR-0012 ею владеет DevOps.
