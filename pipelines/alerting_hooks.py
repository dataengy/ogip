"""Back-compat shim — the alerting hook moved to `pipelines._shared.alerting` (Part 3.1, #37)."""

from __future__ import annotations

from pipelines._shared.alerting import notify_flow_failure

__all__ = ["notify_flow_failure"]
