"""
Email notifications for the daily ingestion pipeline.

`send_ingestion_summary` is called once at the end of `run_daily_ingestion`
to email a short summary of the run (counts of new/updated/relevant/etc).
The actual send is delegated to Resend (https://resend.com).

Recipient resolution:
- The recipient list is fetched from Clerk via
  `app.services.clerk.get_summary_email_recipients`, which returns
  every Clerk user who has explicitly opted in via
  `unsafeMetadata.emailIngestionSummary === true`. Default is opted-out, so a
  fresh Clerk user receives nothing until they enable the toggle from their
  account page.

Behaviour:
- If `settings.RESEND_API_KEY` is empty/unset, the function logs a debug
  message and returns silently. This keeps local development friction-free
  for developers who don't have email credentials.
- If no Clerk user has opted in (or the Clerk lookup fails), the function
  logs and returns without sending — an empty recipient list must never
  raise.
- The send is performed in a thread pool via `asyncio.to_thread` because
  the `resend` SDK is synchronous and would otherwise block the event loop.
- All exceptions raised by Resend are caught and logged. A failed summary
  email must not break or roll back the ingestion run.
"""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Any

from app.core.config import settings
from app.services.clerk import get_summary_email_recipients

logger = logging.getLogger(__name__)


def _format_html(summary: dict[str, Any]) -> str:
    """Render the summary dict as a small HTML table for the email body."""
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{html.escape(str(k))}</td>"
        f"<td style='padding:4px 0'><strong>{html.escape(str(v))}</strong></td></tr>"
        for k, v in summary.items()
    )
    return (
        "<div style='font-family:system-ui,sans-serif;font-size:14px'>"
        "<h2 style='margin:0 0 12px 0'>Daily ingestion summary</h2>"
        f"<table style='border-collapse:collapse'>{rows}</table>"
        "</div>"
    )


def _send_sync(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Blocking Resend call — runs inside a thread via asyncio.to_thread."""
    import resend  # local import: only required when an API key is configured

    resend.api_key = settings.RESEND_API_KEY
    return resend.Emails.send(payload)


async def send_ingestion_summary(summary: dict[str, Any]) -> None:
    """
    Send the daily ingestion summary as an email via Resend.

    `summary` is the same dict shape that the pipeline emits on its final
    `step: complete` progress event (counts of new/updated/relevant/etc).
    """
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — skipping ingestion summary email")
        return

    recipients = await get_summary_email_recipients()
    if not recipients:
        logger.debug(
            "No Clerk users opted in to ingestion summary — skipping email"
        )
        return

    payload = {
        "from": settings.INGESTION_SUMMARY_FROM,
        "to": recipients,
        "subject": "ONTEX — daily ingestion summary",
        "html": _format_html(summary),
    }

    try:
        result = await asyncio.to_thread(_send_sync, payload)
        logger.info("Ingestion summary email sent (resend response=%s)", result)
    except Exception as exc:  # noqa: BLE001 — email failure must never break ingestion
        logger.warning("Failed to send ingestion summary email: %s", exc)


if __name__ == "__main__":
    # Manual smoke test — run with: python -m app.services.ingestion_utils.email
    # Requires RESEND_API_KEY + CLERK_SECRET_KEY to be set in your .env, and at
    # least one Clerk user with unsafeMetadata.emailIngestionSummary === true.
    logging.basicConfig(level=logging.INFO)

    sample_summary = {
        "step": "complete",
        "label": "Done (manual test)",
        "search_terms": ["osteosarcoma"],
        "candidates_found": 42,
        "new": 3,
        "updated": 1,
        "skipped_unchanged": 5,
        "reevaluated": 0,
        "relevant": 2,
        "irrelevant": 2,
        "fetch_errors": 0,
        "classify_errors": 0,
    }

    async def _smoke() -> None:
        recipients = await get_summary_email_recipients()
        print(f"Resolved recipients from Clerk: {recipients}")
        print(f"From: {settings.INGESTION_SUMMARY_FROM}")
        print(f"Resend API key configured: {bool(settings.RESEND_API_KEY)}")
        await send_ingestion_summary(sample_summary)

    asyncio.run(_smoke())
