"""
Public API for Clerk-backed helpers.

Re-exports the single helper used by the ingestion pipeline today:
  - get_summary_email_recipients: resolve opted-in admin emails from Clerk.
"""

from app.services.clerk.recipients import get_summary_email_recipients

__all__ = ["get_summary_email_recipients"]
