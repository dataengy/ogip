"""Shared HTTP plumbing for the alerting transports.

Module-level functions rather than a shared client object: every transport needs the same
three lines, and a plain ``httpx.post`` is what ``respx`` mocks in the unit tests.
"""

from __future__ import annotations

from typing import Any, cast

import httpx

__all__ = ["get_json", "post_json"]

_TIMEOUT = 10.0  # alerting must fail fast — a slow alert must not stall the caller


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST *payload* as JSON. Raises on a non-2xx status; returns the decoded body.

    Some backends answer 200 with a plain ``ok`` string rather than JSON (Slack webhooks
    do exactly this), so a body that will not decode is reported as ``{"raw": <text>}``
    instead of raising — the status code already carried the verdict.
    """
    response = httpx.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
    response.raise_for_status()
    return _decode(response)


def get_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """GET and decode JSON. Raises on a non-2xx status."""
    response = httpx.get(url, headers=headers, timeout=_TIMEOUT)
    response.raise_for_status()
    return _decode(response)


def _decode(response: httpx.Response) -> dict[str, Any]:
    try:
        body: Any = response.json()
    except ValueError:
        return {"raw": response.text}
    if isinstance(body, dict):
        return cast("dict[str, Any]", body)
    return {"raw": body}
