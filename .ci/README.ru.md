<!-- ru-translation-of: .ci/README.md sha:a369ebc117a6 -->
<!-- Автоперевод. Источник — .ci/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `.ci/` — общая библиотека CI-шагов

`run.sh <step>` — единая точка входа; GitHub Actions (`.github/workflows/ci.yml`) — тонкий
фронтенд, который её вызывает, поэтому пайплайны остаются воспроизводимыми и запускаемыми локально (`make ci`).

| Шаг | Что делает |
|---|---|
| `lint` | ruff check + format + SQL-линт (`sql-lint`) |
| `typecheck` | pyright strict |
| `test` | pytest smoke + unit (junit-артефакт) |
| `bash-lint` | shellcheck + shfmt по отслеживаемым `*.sh` |
| `structure-validate` | root-lean-гард (никаких лишних файлов в корне репозитория) |
| `secret-scan` | gitleaks (вся история) |
