<!-- ru-translation-of: docs/RU-DOCS-BRANCH.md sha:897e08259d29 -->
<!-- Автоперевод. Источник — docs/RU-DOCS-BRANCH.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [RU-DOCS-BRANCH.md](RU-DOCS-BRANCH.md)

# Ветка `ru-docs` — версионируемые русские переводы

Долгоживущая ветка (worktree: `../OGIP.worktrees/ru-docs`), никогда не вливается в `dev`
([#55](https://github.com/dataengy/ogip/issues/55)). Она существует потому, что на `dev`
каждый `*.ru.md` **gitignored по замыслу** — переводы там локальны для машины и умерли бы
вместе с рабочей станцией. Эта ветка — **двуязычное представление**: переводы добавлены
принудительно (`git add -f`) и запушены, а mirror-refs в начале файлов (EN-док ↔ RU-сосед)
существуют **только здесь** — на `dev` такие ссылки были бы битыми в каждом клоне.

| Артефакт | dev | ru-docs |
|---|---|---|
| Переводы `*.ru.md` | gitignored, не трекаются | закоммичены (`git add -f`) |
| EN→RU mirror-ref в источниках | отсутствует | есть (после H1) |
| RU→EN mirror-ref в переводах | н/п | есть (после provenance-заголовка) |
| Манифест `docs/TRANSLATIONS.ru.{yml,md}` | производный, не трекается | закоммичен |

## Цикл обновления (выполняется внутри этого worktree)

```bash
git merge origin/dev                     # bring in fresh sources (see conflict note below)
JF=~/.ai/skills/_scripts/docs/translate-ru/Justfile
just -f "$JF" enumerate --scope all      # missing/stale sources (mtime); manifest sha is authority
# translate the listed sources (/translate-md-docs-to-russian — model step)
just -f "$JF" mirror-refs --repo "$PWD" --sources-file <list> --sha-bump --skip-sha-file <stale>
just -f "$JF" manifest-all               # from the worktree root
git add -f -- '*.ru.md' docs/TRANSLATIONS.ru.yml && git add -A
git commit && git push origin ru-docs    # verify origin/ru-docs..ru-docs first, separately
```

Известные ловушки (все подтверждены на практике): каждому рецепту, кроме `enumerate`, нужен
АБСОЛЮТНЫЙ `--repo` (just резолвит `.` относительно каталога Justfile); `enumerate --paths`
молча берёт ОДИН путь за вызов; свежескопированный/свежевыгруженный `.ru.md` обманывает
mtime-проверку устаревания — доверяйте состояниям `sha` в манифесте.

## Конфликты слияния с dev

Строка EN mirror-ref стоит сразу после H1, поэтому dev-правка в начале файла может дать
конфликт при merge. Разрешение всегда одно: оставить контент dev **и** оставить строку
mirror-ref ветки. Содержательное изменение на dev делает записанный sha устаревшим → файл
попадёт в следующий проход enumerate/manifest на ретрансляцию.

## Чего здесь никогда не должно происходить

- Никаких merge/PR из `ru-docs` в `dev` (это принесло бы трекаемые переводы и EN-строки
  ссылок в каждый клон). С 2026-08-20 это закреплено
  ([#57](https://github.com/dataengy/ogip/issues/57)): `ru-docs` **защищена как ветка**
  (нет удаления, нет force-push) и **исключена из squash-only правил мёржа PR** — она
  указана в `never_merge` + `long_lived` в
  `~/.ai/skills/.settings/branch_rules.yml#pr_merge`. Обновляется она только через
  `git merge origin/dev` внутри этого worktree.
- Никаких ручных правок тел `*.ru.md` — правьте EN-источник и ретранслируйте (об этом
  говорит сам provenance-заголовок).
- Никаких коммитов переводов `*.local.md` / машинно-локальных источников (их EN-оригиналы
  не трекаются на dev; осиротевшие RU-файлы остаются нетрекаемыми и здесь).
