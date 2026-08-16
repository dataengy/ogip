<!-- ru-translation-of: src/tests/README.md sha:a52b843b4fb5 -->
<!-- Автоперевод. Источник — src/tests/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `src/tests/` — набор тестов (четыре уровня)

| Уровень | Маркер | Область | Где запускается |
|---|---|---|---|
| **smoke** | `@pytest.mark.smoke` | самая дешёвая проверка связности (импорты, рендер конфигов) — без сервисов | pre-commit, CI |
| **unit** | _(без маркера)_ | чистая логика, без внешних сервисов | CI (`make test`) |
| **integration** | `@pytest.mark.integration` | обращается к Postgres / MinIO (нужен `make up`) | `make test-integration` |
| **e2e** | `@pytest.mark.e2e` | **прогоняет Prefect-джоб end-to-end и проверяет результаты** | `make test-e2e` |

`make test` запускает smoke + unit (быстро, паритет с CI). Integration/e2e требуют Docker-сервисов и
запускаются явно / после `make up`. Режим импорта — `importlib` (файлы `__init__.py` не нужны).
