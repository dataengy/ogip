# `src/tests/` — test suite (four tiers)

| Tier | Marker | Scope | Runs |
|---|---|---|---|
| **smoke** | `@pytest.mark.smoke` | cheapest wiring (imports, config renders) — no services | pre-commit, CI |
| **unit** | _(unmarked)_ | pure logic, no external services | CI (`make test`) |
| **integration** | `@pytest.mark.integration` | touches Postgres / MinIO (need `make up`) | `make test-integration` |
| **e2e** | `@pytest.mark.e2e` | **runs a Prefect job end-to-end and asserts the results** | `make test-e2e` |

`make test` runs smoke + unit (fast, CI parity). Integration/e2e need Docker services and are
run explicitly / after `make up`. Import mode is `importlib` (no `__init__.py` needed).
