<!-- ru-translation-of: .ai/tasks/finalization.md sha:5f95b5304d7f -->
<!-- Автоперевод. Источник — .ai/tasks/finalization.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [finalization.md](finalization.md)

# Задача — Финализация: приземлить всё, три зелёные run-команды, dev→main

**Статус:** ✅ сделано (2026-07-30, в тот же день) · **Приоритет:** **P1** ·
**Issue:** [#43](https://github.com/dataengy/ogip/issues/43)

Зонтик над финализационным прогоном; действующий план —
[docs/superpowers/plans/2026-07-30-finalization-land-everything.md](../../docs/superpowers/plans/2026-07-30-finalization-land-everything.md).
Режим: AUTO (директива владельца) — без пофазных гейтов утверждения; чекпойнт-отчёты после B/C/D.

## Цель («готово»)

- `make run-dbt` · `make run-bruin` · `make run-dagster-dbt` — все зелёные E2E на сэмпл-данных.
- Ре-рут T4–T9 сделан (#40): dbt+bruin как primary в конфиге, Makefile, гейтах, AGENTS.md; ADR-0020.
- Lane'ы приземлены или громко заморожены: dagster PR #34, odos #37; placeholder-ветки удалены.
- DQ-мониторы исполняются (ненулевой код при отказе) — или громко отложены, но никогда не «молча зелёные».
- PR #10 dev → main смержен, CI зелёный, main готов к релизу.
- Витринная дека (внешний репозиторий deck-generator) + черновики аутрича — контент остаётся вне репозитория.

## Чек-лист (фазы)

- [x] **A** — расчистка: safety-push odos · сломаны 3 протухших лока · восстановлен повреждённый
      `pipelines/dbt/prefect.yaml` · локальный `dev` согласован (== origin/dev)
- [x] **A0** — апсерт planning/tasking-доков + tasks-sync + триаж issues (#43/#44 созданы;
      #28/#30/#31 закрыты; F6 починен; работа соседней сессии спасена+доделана → PR #45 смержен)
- [x] **B** — три зелёные run-команды (`run-dbt` · `run-bruin` · `run-dagster-dbt`, все
      exit 0, выходы 5/5/5) + громкая DQ-заглушка; починены 3 латентных бага путей (dbt/bruin/dagster)
- [x] **C** — ре-рут T4–T9 сделан, PR #46 смержен (T8 пропущен по дизайну; ADR-0020; #40 закрыт)
- [x] **D** — ✓ выведенные из работы ветки помечены как stale (сохранены — директива владельца; каталоги worktree выведенных lane'ов удалены) · ✓ DQ-исполнитель (PR #47, находка первого же дня:
      пустой console_pricing → демо согласовано) · ✓ развёртка TBD + триаж issues (#39/#40/#44
      закрыты, 6 замороженных issues несут указатели на техдолг) · ✓ обновление доков · ✓ dagster
      PR #34 смержен (кастомные проверки: скалярная семантика Bruin, dbt разворачивает) · ✓ odos PR #49
      смержен (чистый; адаптеры остаются на #37) · ✓ PR #10 dev→main СМЕРЖЕН — main выпущен
- [x] **E** — дека СОБРАНА и провалидирована (31 слайд, репозиторий deck-factory, pptx+html в ~/Downloads);
      черновики аутрича записаны в `.ai/outreach-drafts.local.md` (исключён из индекса) — слить с базовыми
      черновиками из TG-треда вручную

## Приёмка

- CI зелёный на `dev` и `main`; каждая неактивная ветка перечислена в
  [docs/techdebt/stale-branches.md](../../docs/techdebt/stale-branches.md) (сохранены, помечены —
  никогда не удаляются); STATUS/ROADMAP/техдолг устаревают не более чем на 1 день; у каждой
  отложенной фичи есть громкая заглушка + строка в [docs/techdebt/finalization-tbd.md](../../docs/techdebt/finalization-tbd.md)
  + issue.
