<!-- ru-translation-of: config/README.md sha:198c6a0aacc6 -->
<!-- Автоперевод. Источник — config/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `config/` — конфигурация (SSoT)

Каждый несекретный дефолт объявлен здесь **один раз**. Ничего конфигоподобного не живёт в
корне репозитория.

| Файл | Назначение |
|---|---|
| `config.yml` | **Единственный источник истины** — пути, порты, storage, Postgres, профили, источники. Python читает его напрямую; `.env` — производный от него. |
| `.env-render.py` | Рендерит плоский корневой `.env` из `config.yml` (производные значения + пустые слоты секретов; merge-safe по секретам). `make render-env`. |
| `.pre-commit-config.yaml` | Хуки, запускаемые **prek** (быстро): ruff · sqlfluff (SQL) · shellcheck/shfmt (Bash) · yamllint · gitleaks · ty · smoke-тесты (+ data-тесты на push). |
| `.yamllint.yaml` | Смягчённый конфиг YAML-линта. |
| `sqlfluff/` | Пресеты SQL-линта по диалектам (домашний стиль DuckDB также в `pyproject.toml`). |
| `.env-secrets-render.sh` | _(opt-in)_ заполнение слотов секретов из Bitwarden / git-secret (ADR-0011). Действия: `pull` (merge-safe заполнение) · `push` (upsert в vault bw) · `hide`/`reveal` (git-secret) · `setup-git-secret` · `doctor`. Just-рецепты: `secrets-render[-dry]`, `secrets-push[-dry]`, `secrets-hide[-dry]`, `secrets-reveal`, `secrets-setup-git-secret`, `secrets-doctor`. Путь по умолчанию остаётся ручным: `.env` / секреты GitHub Actions. |
| `secrets/` | рабочая директория git-secret: коммитимые блобы `*.secret` + gitignored plaintext ([README](secrets/README.md)). |

**Никогда** не кладите сюда значения секретов — трекаемые шаблоны несут только пустые слоты
/ имена env-переменных.
