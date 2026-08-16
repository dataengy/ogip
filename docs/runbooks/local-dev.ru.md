<!-- ru-translation-of: docs/runbooks/local-dev.md sha:0cb7a3c7c886 -->
<!-- Автоперевод. Источник — docs/runbooks/local-dev.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [local-dev.md](local-dev.md)

# Runbook — Локальная инициализация разработки

- **Триггер:** первичная настройка или обновление локального checkout.
- **Ответственный:** любой контрибьютор.

## Предусловия

- [uv](https://docs.astral.sh/uv/), Docker Compose. Опционально: [just](https://just.systems/).
- Секреты: заполните слоты gitignored-файла `.env` вручную (или `just secrets-render` для опционального бэкенда).

## Шаги

1. `make bootstrap` — uv → `.run/venv`, хуки pre-commit, рендер `.env` из `config/config.yml`.
2. `make check` — ruff + pyright strict + pytest (паритет с CI).
3. `make up` — запуск основных сервисов в Docker (Postgres; Prefect; MinIO, если этого требует профиль хранилища).
4. `make run` — прогон конвейера на встроенных примерных данных (ключи API не требуются).

## Проверка

- `make check` зелёный; `make up` сообщает о здоровых контейнерах; `make run` пишет `.run/outputs/*.parquet`.

## Откат

- `make down` останавливает сервисы; удалите `.run/`, чтобы сбросить всё runtime-состояние (безопасно — gitignored).

## Эскалация

- Проблемы окружения/Docker, не связанные с кодом: инфраструктура/DevOps обслуживаются отдельно.
