<!-- ru-translation-of: config/secrets/README.md sha:43d8ed3e1b51 -->
<!-- Автоперевод. Источник — config/secrets/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `config/secrets/` — рабочая директория git-secret (opt-in, ADR-0011)

Дом opt-in бэкенда **git-secret**
([ADR-0011](../../docs/adr/ADR-0011-minimal-secrets.md) ·
[docs/comparisons/secrets-management.md](../../docs/comparisons/secrets-management.md)).

| Файл | Трекается? | Что это |
|---|---|---|
| `.env.secrets` | **никогда** (gitignored) | plaintext-экспорт `KEY=VALUE` заполненных слотов секретов из корневого `.env` |
| `.env.secrets.secret` | **да** | GPG-шифрованный блоб — безопасно коммитить; именно он синхронизирует машины |
| `README.md` | да | этот файл |

Правила игнорирования в корневом `.gitignore` обеспечивают ровно это разделение: всё в этой
директории игнорируется, **кроме** README и блобов `*.secret`.

## Поток

```bash
just secrets-setup-git-secret   # one-time: git secret init + tell + add (needs a GPG key)
just secrets-hide               # .env filled slots -> .env.secrets -> .env.secrets.secret
git add config/secrets/*.secret .gitsecret && git commit   # blob + keyring metadata
# ...on the new workstation (with the same GPG key imported):
just secrets-render             # reveal + fill the blank slots of .env
```

Имена слотов объявлены один раз в `config/.env-render.py` (`SECRET_SLOTS`); этот бэкенд
никогда не изобретает собственный список. `just secrets-doctor` сообщает готовность
(наличие GPG-ключа, состояние init, наличие блоба), ничего не записывая.

**Никогда** не коммитьте сюда plaintext — `git secret hide` — единственный путь от `.env`
до коммитимого артефакта.
