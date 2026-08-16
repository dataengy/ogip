<!-- ru-translation-of: docs/runbooks/new-workstation.md sha:2c2edda216d2 -->
<!-- Автоперевод. Источник — docs/runbooks/new-workstation.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [new-workstation.md](new-workstation.md)

# Ранбук — Бутстрап R&D OGIP на новой рабочей станции

- **Триггер:** перенос R&D на свежую машину; репозиторий должен приехать целиком (код +
  секреты + воспроизводимое окружение), ничего не оставив на старой.
- **Владелец:** владелец репозитория. **Серьёзность/срочность:** плановая миграция, не инцидент.

## Предусловия

- На **старой** машине всё осело: `just preflight` говорит `clean`
  (нет грязных worktree, нет незапушенных веток в единственной копии, нет протухших локов).
- Секреты депонированы через один из opt-in бэкендов
  ([сравнение](../comparisons/secrets-management.md)): `just secrets-push` (Bitwarden) или
  `just secrets-hide` + закоммиченный блоб (git-secret).
- Новая машина: macOS/Linux с Homebrew или аналогичным пакетным менеджером.

## Шаги

1. Установить тулчейн:

   ```bash
   brew install git git-lfs uv just gh jq        # core
   brew install bitwarden-cli                    # if secrets.backend = bitwarden
   brew install git-secret gnupg                 # if secrets.backend = git-secret
   git lfs install
   ```

2. Склонировать и войти (большие тестовые датасеты — это LFS-объекты, тяните их явно):

   ```bash
   git clone https://github.com/dataengy/ogip.git && cd ogip
   git lfs pull
   ```

3. Отрендерить конфиг и собрать окружение (первый запуск `uv` строит `.run/venv` — занимает
   минуты):

   ```bash
   make render-env
   uv sync
   ```

4. Заполнить слоты секретов из своего бэкенда:

   ```bash
   just secrets-doctor                            # readiness report, read-only
   # Bitwarden path:
   bw login && export BW_SESSION="$(bw unlock --raw)"
   just secrets-render-dry && just secrets-render
   # git-secret path (import your GPG key first):
   bash config/.env-secrets-render.sh pull --backend git-secret
   ```

5. Пересоздать нужные lane-worktree (worktree локальны для машины, lane живут на origin):

   ```bash
   git worktree add ../OGIP.worktrees/<name> lane/<name>
   ```

6. Гейт и запуск:

   ```bash
   make check
   make run
   ```

## Проверка

- `just secrets-doctor` показывает каждый слот `set` (или осознанно `blank`).
- `make check` зелёный; `make run` завершается на sample-данных.
- `git status` чистый; `git log --oneline -3` совпадает с origin/dev.

## Откат

- Ничего здесь не мутирует origin — неудачный бутстрап лечится повторным клонированием.
- Неверно заполненные секреты: перезапустите `make render-env` (merge-safe рендер сохраняет
  только подтверждённое) или очистите слот вручную и снова `just secrets-render`.

## Эскалация

- Бэкенд секретов неработоспособен → громкая ошибка `doctor`/`pull` называет точное
  лекарство (команда разблокировки, отсутствующий GPG-ключ). Инфраструктура/DevOps сверх
  этого обрабатывается отдельно
  ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)).
