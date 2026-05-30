"""
Resolve the recipient list for the daily ingestion summary email from Clerk.

Admins authenticate via Clerk, which holds their email addresses and per-user
metadata. Rather than maintain a static list of recipients in env vars, we
query Clerk's Backend API for every user and keep only those who have
explicitly opted in via `unsafeMetadata.emailIngestionSummary === true`.

The opt-in flag is written from the frontend through Clerk's `useUser().update`
hook, so no backend write endpoint is required.

Failure mode: any error talking to Clerk is logged as a warning and the
function returns an empty list. The caller (`send_ingestion_summary`) must
tolerate an empty list — a Clerk outage must never break ingestion.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CLERK_API = "https://api.clerk.com/v1"
# Clerk's `GET /v1/users` endpoint accepts limit up to 500. ONTEX has only a
# handful of admins today; revisit pagination if we cross ~400 users.
_USER_LIMIT = 500


def _primary_email(user: dict[str, Any]) -> str | None:
    """Return the user's primary verified email, or None if not resolvable."""
    primary_id = user.get("primary_email_address_id")
    for entry in user.get("email_addresses", []):
        if entry.get("id") == primary_id:
            return entry.get("email_address")
    return None


def _is_opted_in(user: dict[str, Any]) -> bool:
    """True only if the user explicitly set the opt-in flag to True."""
    meta = user.get("unsafe_metadata") or {}
    return meta.get("emailIngestionSummary") is True


async def get_summary_email_recipients() -> list[str]:
    """
    Return the email addresses of every Clerk user who has explicitly opted IN
    to the daily ingestion summary.

    Default is opted-OUT: only users with
    `unsafeMetadata.emailIngestionSummary === true` are included. Any other
    value (missing/null/false) means "do not send".
    """
    if not settings.CLERK_SECRET_KEY:
        logger.warning("CLERK_SECRET_KEY not set — cannot resolve summary recipients")
        return []

    headers = {"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}
    params = {"limit": _USER_LIMIT}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{_CLERK_API}/users", headers=headers, params=params
            )
            response.raise_for_status()
            users = response.json()
    except Exception as exc:  # noqa: BLE001 — failure must never break ingestion
        logger.warning("Failed to fetch Clerk users: %s", exc)
        return []

    recipients: list[str] = []
    for user in users:
        if not _is_opted_in(user):
            continue
        email = _primary_email(user)
        if email:
            recipients.append(email)

    # Dedupe while preserving order.
    seen: set[str] = set()
    deduped = [e for e in recipients if not (e in seen or seen.add(e))]
    return deduped
