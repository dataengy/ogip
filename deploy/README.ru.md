<!-- ru-translation-of: deploy/README.md sha:bf40966c9af6 -->
<!-- Автоперевод. Источник — deploy/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# deploy/ — локальный и VPS runtime-стеки

Compose-стеки для сервисов, с которыми работает OGIP. Всё управляется из SSoT
(`config/config.yml` → отрендеренный `.env` через `make render-env`) — никогда не хардкодьте
здесь порт, бакет или пользователя; добавьте их в SSoT и ссылайтесь через `${VAR}`.

| Файл | Стек | Команды |
|---|---|---|
| `docker-compose.yml` | **base**: Postgres, Prefect server, MinIO (профиль `storage`) | `make up` · `make storage-up` · `make down` |
| `obs/docker-compose.obs.yml` | **observability**: VictoriaMetrics, Loki, Alloy, Grafana | `make obs-up` · `make obs-down` |

Оба проекта используют общую внешнюю сеть `ogip`, объявленную базовым стеком.

## Сервисы

- **postgres** — landing-зона + `platform_meta` + бэкенд Prefect (ADR-0008 / D9).
- **prefect** — сервер Prefect для runtime-профиля `server`. **Runtime по умолчанию —
  эфемерный** (D3), поэтому `make run` вообще не требует сервера.
- **minio** + **minio-init** — S3-совместимое объектное хранилище для lake-профиля `minio`
  (D2 / [ADR-0003](../docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md)). Скрыто за
  профилем `storage`, поэтому `make up` остаётся лёгким. `minio-init` создаёт raw-бакет, чтобы
  первому запуску было куда приземлить данные. См. [docs/architecture/storage.md](../docs/architecture/storage.md).

## Учётные данные

`.env` находится в gitignore; секреты — пустые слоты, заполняемые вручную или через GitHub
Actions (ADR-0011 / D10). Фоллбэки `${VAR:-default}` здесь зеркалируют литералы SSoT, чтобы
стек поднимался даже из голого чекаута.

**Root**-учётные данные MinIO (`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) намеренно отделены
от **клиентских** учётных данных OGIP (`OGIP_S3_*`): клиентские слоты могут содержать реальный
ключ AWS или R2, а скармливать реальный ключ локальному контейнеру в качестве его root-пароля —
верный способ выстрелить себе в ногу. Для профиля `minio` эти две пары должны совпадать —
`config/.env-render.py` поставляет обе как dev-значения по умолчанию
(`ogipminio` / `ogipminio123`); это одноразовые локальные литералы, **не** секреты.

## VPS

Деплой ручной (ADR-0012); DevOps ведётся отдельно. См.
[docs/runbooks/](../docs/runbooks/).
