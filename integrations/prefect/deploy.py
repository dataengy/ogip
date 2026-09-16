"""TBD #11/#17 — Prefect deployment registration is NOT implemented.

`deploy/vps/deploy.sh` step 5 and `just prefect-deploy` call this file; it exits loudly
(2) instead of half-deploying or dying with FileNotFoundError. Writing it requires the
pinned run model decision to be acted on (ephemeral pinned 2026-07-30; a served/worker
deployment is V2 scope — docs/techdebt/finalization-tbd.md rows 6 and 8).
"""

import sys

sys.stderr.write(
    "integrations/prefect/deploy.py: TBD — deployment registration is deliberately not "
    "implemented yet (issues #11/#17; docs/techdebt/finalization-tbd.md row 6).\n"
)
sys.exit(2)
