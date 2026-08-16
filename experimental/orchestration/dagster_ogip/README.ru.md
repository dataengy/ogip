<!-- ru-translation-of: experimental/orchestration/dagster_ogip/README.md sha:eed60a89fc4b -->
<!-- Автоперевод. Источник — experimental/orchestration/dagster_ogip/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# dagster_ogip

## Начало работы

### Установка зависимостей

**Вариант 1: uv**

Убедитесь, что [`uv`](https://docs.astral.sh/uv/) установлен согласно
[официальной документации](https://docs.astral.sh/uv/getting-started/installation/).

Создайте виртуальное окружение и установите требуемые зависимости через _sync_:

```bash
uv sync
```

Затем активируйте виртуальное окружение:

| ОС | Команда |
| --- | --- |
| MacOS | ```source .venv/bin/activate``` |
| Windows | ```.venv\Scripts\activate``` |

**Вариант 2: pip**

Установите python-зависимости с помощью [pip](https://pypi.org/project/pip/):

```bash
python3 -m venv .venv
```

Затем активируйте виртуальное окружение:

| ОС | Команда |
| --- | --- |
| MacOS | ```source .venv/bin/activate``` |
| Windows | ```.venv\Scripts\activate``` |

Установите требуемые зависимости:

```bash
pip install -e ".[dev]"
```

### Запуск Dagster

Запустите веб-сервер Dagster UI:

```bash
dg dev
```

Откройте http://localhost:3000 в браузере, чтобы увидеть проект.

## Узнать больше

Чтобы узнать больше об этом шаблоне и о Dagster в целом:

- [Документация Dagster](https://docs.dagster.io/)
- [Dagster University](https://courses.dagster.io/)
- [Slack-сообщество Dagster](https://dagster.io/slack)
