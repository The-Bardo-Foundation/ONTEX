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
- If `settings.RESEND_API_KEY` or `settings.INGESTION_SUMMARY_FROM` is
  empty/unset, the function logs and returns before contacting Clerk. Both
  are checked up front so an unconfigured deployment does not make a pointless
  authenticated API call on every run. This also keeps local development
  friction-free for developers who don't have email credentials.
- If no Clerk user has opted in (or the Clerk lookup fails), the function
  logs and returns without sending — an empty recipient list must never
  raise.
- One email is sent per recipient rather than a single message with a shared
  `to` list, so admins are not exposed to each other's addresses and one bad
  address cannot block delivery to everyone else.
- Each send is performed in a thread pool via `asyncio.to_thread` because
  the `resend` SDK is synchronous and would otherwise block the event loop.
- Every failure path is caught and logged. `run_daily_ingestion` awaits this
  function unguarded after the run is already committed, so anything escaping
  here would surface as `_ingestion_status["error"]` and report a fully
  successful run as failed.
"""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Any

from app.core.config import settings
from app.services.clerk import get_summary_email_recipients

logger = logging.getLogger(__name__)


# Keys that carry progress-stream plumbing rather than run results. `step` is
# always the literal "complete" here, and `label` is promoted to the subtitle
# instead of being rendered as a table row.
_INTERNAL_KEYS = {"step", "label"}


def _humanise(key: str) -> str:
    """`skipped_unchanged` → `Skipped unchanged`."""
    return key.replace("_", " ").capitalize()


def _format_value(value: Any) -> str:
    """Render a summary value readably — lists as prose, not Python reprs."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "—"
    return str(value)


def _format_html(summary: dict[str, Any]) -> str:
    """Render the summary dict as a small HTML table for the email body."""
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{html.escape(_humanise(k))}</td>"
        f"<td style='padding:4px 0'><strong>{html.escape(_format_value(v))}</strong></td></tr>"
        for k, v in summary.items()
        if k not in _INTERNAL_KEYS
    )
    # `label` distinguishes a normal run from the "no trials to process" exit,
    # which matters because the counts below are candidates found, not work done.
    subtitle = summary.get("label")
    subtitle_html = (
        f"<p style='margin:0 0 12px 0;color:#555'>{html.escape(str(subtitle))}</p>"
        if subtitle
        else ""
    )
    return (
        "<div style='font-family:system-ui,sans-serif;font-size:14px'>"
        "<h2 style='margin:0 0 4px 0'>Daily ingestion summary</h2>"
        f"{subtitle_html}"
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
    # Both config guards run before the Clerk lookup: they are free to check,
    # and bailing afterwards would waste an authenticated API call every run.
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — skipping ingestion summary email")
        return

    if not settings.INGESTION_SUMMARY_FROM:
        logger.warning(
            "INGESTION_SUMMARY_FROM not set — skipping ingestion summary email"
        )
        return

    # get_summary_email_recipients() already swallows its own failures, but it
    # is awaited defensively here too: this function is called unguarded at the
    # end of run_daily_ingestion, so anything escaping would mark an otherwise
    # successful run as failed in the admin UI.
    try:
        recipients = await get_summary_email_recipients()
    except Exception as exc:  # noqa: BLE001 — must never break ingestion
        logger.warning("Failed to resolve ingestion summary recipients: %s", exc)
        return

    if not recipients:
        logger.debug(
            "No Clerk users opted in to ingestion summary — skipping email"
        )
        return

    body = _format_html(summary)

    # One email per recipient rather than a shared `to` list, so admins are not
    # exposed to each other's addresses and one bad address cannot block the
    # rest. The list is a handful of people, so the extra calls are cheap.
    sent = 0
    for recipient in recipients:
        payload = {
            "from": settings.INGESTION_SUMMARY_FROM,
            "to": [recipient],
            "subject": "ONTEX — daily ingestion summary",
            "html": body,
        }
        try:
            await asyncio.to_thread(_send_sync, payload)
            sent += 1
        except Exception as exc:  # noqa: BLE001 — email failure must never break ingestion
            logger.warning(
                "Failed to send ingestion summary email to %s: %s", recipient, exc
            )

    logger.info("Ingestion summary email sent to %d/%d recipient(s)", sent, len(recipients))


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
