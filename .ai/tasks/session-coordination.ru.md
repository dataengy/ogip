<!-- ru-translation-of: .ai/tasks/session-coordination.md sha:0adca1ae58f2 -->
<!-- Автоперевод. Источник — .ai/tasks/session-coordination.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [session-coordination.md](session-coordination.md)

# Задача — Координация сессий: lane'ы, ship-цикл, привязка коммитов к задачам, PR-флоу

**Статус:** 🟡 в работе — lane-блокировки + ship-цикл + привязка коммитов выпущены; worktree'и предложены.

## Почему

Шесть агентских сессий (core-pipeline · obs · evidence · dagster · s3 · vps) работают в **одном
checkout'е**. Без механики сессии заметают файлы друг друга в коммиты, ломают друг другу
gate'ы и дублируют работу. Два реальных инцидента уже случились:

- **Дублирующийся трекер**: две сессии независимо построили tasks-sync; маркеры различались одним
  пробелом (`ogip-task:<slug>` vs `ogip-task: <slug>`) → дублирующиеся issue #4–#7 (удалены).
  Сошлись на `src/scripts/tasks_sync.py`.
- **Межлейновая поломка gate'а**: незавершённый `src/ogip/storage.py` из lane s3 сделал
  `make check` красным и заблокировал ship несвязанной lane.

## Сделано

- `src/scripts/lane.sh` — `settle` (fetch · drift · dirty · инвентаризация lock'ов) + `acquire`/`check`/
  `release`, делегирует глобальному примитиву `agent-session-lock.sh` (без новой логики блокировок).
- `src/scripts/ship.sh` — `lane guard → settle → make check → scoped commit → push → watch CI →
  tasks-sync → tg-inform`. Никогда не делает `git add -A`; стейджит allowlist своей lane и **снимает
  со стейджа спорные SSoT-файлы** (pyproject/Justfile/config.yml/STATUS.md), если сессия не держит их lock.
- `src/scripts/check-commit-msg.sh` + prek-хук `commit-msg` — **каждый коммит обязан ссылаться на
  issue** (`Refs: #N`). Учитывает комментарии (голая строка `#12` — это git-комментарий, а не привязка);
  merge/revert/fixup освобождены.
- Флоу веток: работа на **`dev`**, PR → `main`. CI гоняется на пушах в `main`/`dev` и на PR.

## Проверено

- `lane settle` перечисляет живые lock'и + drift; acquire/check lock'а проходят round-trip.
- Хук commit-msg: отклоняет непривязанный коммит, принимает `Refs: #N`, отклоняет `#12` только в комментарии, освобождает merge'и.
- Все 4 файла задач несут issue (#1 #2 #3 #8) через `just tasks-sync`.

## Worktree'и — структурное решение (сделано)

`src/scripts/worktree.sh` даёт **каждой lane собственный рабочий каталог + ветку** поверх одного
`.git`. Это устраняет опасности общего дерева в корне, а не смягчает их.

```bash
bash src/scripts/worktree.sh add <lane>     # ../OGIP.worktrees/<lane> on branch lane/<lane> off dev
bash src/scripts/worktree.sh list|path|remove <lane>
cd "$(bash src/scripts/worktree.sh path obs)" && make bootstrap
```

| Lane | Worktree | Ветка |
|---|---|---|
| core-pipeline | `OGIP/` (интеграционный checkout) | `dev` |
| obs · evidence · dagster · s3 · vps | `OGIP.worktrees/<lane>` | `lane/<lane>` |

**Флоу:** `lane/<x>` → PR → `dev` → PR → `main`. Каждая lane получает собственный gate (красный файл в одной
lane больше не может блокировать другую), собственный HEAD (`git checkout` перестаёт двигаться под другими
сессиями), и `git add -A` снова безопасен внутри lane. Lock'и теперь охраняют **merge'и**, а не файлы.

Дёшево: worktree'и разделяют object store, а uv хардлинкает каждый venv из своего общего кэша.

## Открыто / предложено
- Upstream-баг: рецепт `just agent-lock` из `/agent-session-lock` повторно парсит `--reason` через
  `bash -c`, поэтому скобки его роняют; прямой скрипт работает.
- **D20**: внести эти scaffold-стандарты в `~/.ai/skills/.settings/code_specs/`.
- Давление на диск: 6 сессий × uv-окружения на томе ~13G один раз упёрлись в ENOSPC (кэш uv 1.3G).
