"""TBD #11/#17 — remote flow triggering is NOT implemented.

`deploy/vps/smoke.sh` calls this file; it exits loudly (2) instead of dying with
FileNotFoundError. Lands together with deploy.py once a server-side run model exists
(docs/techdebt/finalization-tbd.md rows 6 and 8).
"""

import sys

sys.stderr.write(
    "integrations/prefect/trigger.py: TBD — remote triggering is deliberately not "
    "implemented yet (issues #11/#17; docs/techdebt/finalization-tbd.md row 6).\n"
)
sys.exit(2)
