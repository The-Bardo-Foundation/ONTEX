"""
Unit tests for the daily ingestion summary email (pipeline Step 8).

Covers two modules:
  - app.services.clerk.recipients   — resolving opted-in recipients from Clerk
  - app.services.ingestion_utils.email — rendering and sending the summary

The behaviour these lock down matters because `run_daily_ingestion` awaits
`send_ingestion_summary` *unguarded*, after the run has already been committed.
Anything that escapes this code path gets caught by the ingestion endpoint and
reported as `_ingestion_status["error"]` — i.e. a fully successful run shows up
in the admin UI as failed. Several tests below exist purely to pin that down.
"""

import pytest

from app.core.config import settings
from app.services.clerk import recipients as recipients_mod
from app.services.clerk.recipients import (
    _is_opted_in,
    _primary_email,
    get_summary_email_recipients,
)
from app.services.ingestion_utils import email as email_mod
from app.services.ingestion_utils.email import _format_html, send_ingestion_summary


# ── Fake httpx plumbing ───────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response=None, get_exc=None):
        self._response = response
        self._get_exc = get_exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, *_, **__):
        if self._get_exc:
            raise self._get_exc
        return self._response


def _patch_clerk_response(monkeypatch, payload=None, raise_exc=None, get_exc=None):
    """Point recipients.httpx.AsyncClient at a canned response."""
    monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "sk_test_123")
    response = _FakeResponse(payload, raise_exc=raise_exc)
    monkeypatch.setattr(
        recipients_mod.httpx,
        "AsyncClient",
        lambda **__: _FakeClient(response=response, get_exc=get_exc),
    )


def _user(email, opted_in, user_id="u1"):
    """Build a Clerk-shaped user dict."""
    return {
        "id": user_id,
        "primary_email_address_id": f"idn_{user_id}",
        "email_addresses": [{"id": f"idn_{user_id}", "email_address": email}],
        "unsafe_metadata": {"emailIngestionSummary": opted_in},
    }


# ── _primary_email ────────────────────────────────────────────────────────────


def test_primary_email_resolves_the_primary_address():
    user = {
        "primary_email_address_id": "idn_2",
        "email_addresses": [
            {"id": "idn_1", "email_address": "secondary@example.com"},
            {"id": "idn_2", "email_address": "primary@example.com"},
        ],
    }
    assert _primary_email(user) == "primary@example.com"


def test_primary_email_returns_none_when_no_entry_matches():
    user = {
        "primary_email_address_id": "idn_9",
        "email_addresses": [{"id": "idn_1", "email_address": "a@example.com"}],
    }
    assert _primary_email(user) is None


def test_primary_email_handles_null_email_addresses():
    """
    Regression: a `.get(key, [])` default only applies when the key is absent.
    Clerk sending the key with a null value used to raise TypeError here and
    fail the whole ingestion run.
    """
    assert _primary_email({"primary_email_address_id": "x", "email_addresses": None}) is None


def test_primary_email_handles_missing_email_addresses():
    assert _primary_email({"primary_email_address_id": "x"}) is None


def test_primary_email_skips_non_dict_entries():
    user = {
        "primary_email_address_id": "idn_1",
        "email_addresses": ["garbage", {"id": "idn_1", "email_address": "a@example.com"}],
    }
    assert _primary_email(user) == "a@example.com"


# ── _is_opted_in ──────────────────────────────────────────────────────────────


def test_opted_in_only_for_boolean_true():
    assert _is_opted_in({"unsafe_metadata": {"emailIngestionSummary": True}}) is True


@pytest.mark.parametrize(
    "meta",
    [
        {"emailIngestionSummary": False},
        {"emailIngestionSummary": None},
        {"emailIngestionSummary": "true"},  # truthy string must NOT count
        {"emailIngestionSummary": 1},  # truthy int must NOT count
        {},
    ],
)
def test_not_opted_in_for_anything_other_than_true(meta):
    """Default is opted-OUT — inverting this would email people who never asked."""
    assert _is_opted_in({"unsafe_metadata": meta}) is False


def test_not_opted_in_when_metadata_missing_or_null():
    assert _is_opted_in({}) is False
    assert _is_opted_in({"unsafe_metadata": None}) is False


# ── get_summary_email_recipients ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recipients_empty_without_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "")
    assert await get_summary_email_recipients() == []


@pytest.mark.asyncio
async def test_recipients_returns_only_opted_in_users(monkeypatch):
    _patch_clerk_response(
        monkeypatch,
        payload=[
            _user("yes@example.com", True, "u1"),
            _user("no@example.com", False, "u2"),
            _user("also-yes@example.com", True, "u3"),
        ],
    )
    assert await get_summary_email_recipients() == [
        "yes@example.com",
        "also-yes@example.com",
    ]


@pytest.mark.asyncio
async def test_recipients_are_deduped_preserving_order(monkeypatch):
    _patch_clerk_response(
        monkeypatch,
        payload=[
            _user("dup@example.com", True, "u1"),
            _user("other@example.com", True, "u2"),
            _user("dup@example.com", True, "u3"),
        ],
    )
    assert await get_summary_email_recipients() == [
        "dup@example.com",
        "other@example.com",
    ]


@pytest.mark.asyncio
async def test_recipients_empty_on_http_error(monkeypatch):
    _patch_clerk_response(monkeypatch, raise_exc=RuntimeError("401 Unauthorized"))
    assert await get_summary_email_recipients() == []


@pytest.mark.asyncio
async def test_recipients_empty_on_network_error(monkeypatch):
    _patch_clerk_response(monkeypatch, get_exc=RuntimeError("connection reset"))
    assert await get_summary_email_recipients() == []


@pytest.mark.asyncio
async def test_recipients_empty_on_non_list_response(monkeypatch):
    """
    Regression: the response parsing used to sit outside the try/except, so a
    dict body (e.g. a paginated wrapper) raised AttributeError out of the
    pipeline instead of degrading to "no recipients".
    """
    _patch_clerk_response(monkeypatch, payload={"data": [_user("a@example.com", True)]})
    assert await get_summary_email_recipients() == []


@pytest.mark.asyncio
async def test_recipients_survives_malformed_user_entries(monkeypatch):
    """A malformed user must be skipped, not abort the whole lookup."""
    _patch_clerk_response(
        monkeypatch,
        payload=[
            "not-a-dict",
            {"unsafe_metadata": {"emailIngestionSummary": True}, "email_addresses": None},
            _user("good@example.com", True, "u2"),
        ],
    )
    assert await get_summary_email_recipients() == ["good@example.com"]


# ── _format_html ──────────────────────────────────────────────────────────────


def test_format_html_omits_internal_keys():
    body = _format_html({"step": "complete", "label": "Done", "new": 3})
    assert "complete" not in body
    assert ">Step<" not in body


def test_format_html_promotes_label_to_subtitle():
    body = _format_html({"step": "complete", "label": "Done — no trials to process", "new": 0})
    assert "Done — no trials to process" in body


def test_format_html_humanises_keys_and_lists():
    body = _format_html({"skipped_unchanged": 5, "search_terms": ["osteosarcoma", "sarcoma"]})
    assert "Skipped unchanged" in body
    assert "osteosarcoma, sarcoma" in body
    assert "['osteosarcoma'" not in body  # not a Python repr


def test_format_html_escapes_values():
    body = _format_html({"search_terms": ["<script>alert(1)</script>"]})
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


# ── send_ingestion_summary ────────────────────────────────────────────────────


@pytest.fixture
def sent(monkeypatch):
    """Capture Resend payloads instead of sending, and spy on the Clerk lookup."""
    payloads: list[dict] = []
    calls = {"clerk": 0}

    def _fake_send(payload):
        payloads.append(payload)
        return {"id": "msg_1"}

    async def _fake_recipients():
        calls["clerk"] += 1
        return ["admin@example.com"]

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(settings, "INGESTION_SUMMARY_FROM", "noreply@example.com")
    monkeypatch.setattr(email_mod, "_send_sync", _fake_send)
    monkeypatch.setattr(email_mod, "get_summary_email_recipients", _fake_recipients)
    return payloads, calls


SUMMARY = {"step": "complete", "label": "Done", "new": 2}


@pytest.mark.asyncio
async def test_send_skips_without_api_key(monkeypatch, sent):
    payloads, calls = sent
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    await send_ingestion_summary(SUMMARY)
    assert payloads == []
    assert calls["clerk"] == 0, "must not call Clerk when Resend is unconfigured"


@pytest.mark.asyncio
async def test_send_skips_without_from_address_before_calling_clerk(monkeypatch, sent):
    """Both config guards run before the network call, so an unconfigured
    deployment does not make a pointless authenticated request every run."""
    payloads, calls = sent
    monkeypatch.setattr(settings, "INGESTION_SUMMARY_FROM", "")
    await send_ingestion_summary(SUMMARY)
    assert payloads == []
    assert calls["clerk"] == 0


@pytest.mark.asyncio
async def test_send_skips_when_nobody_opted_in(monkeypatch, sent):
    payloads, _ = sent

    async def _none():
        return []

    monkeypatch.setattr(email_mod, "get_summary_email_recipients", _none)
    await send_ingestion_summary(SUMMARY)
    assert payloads == []


@pytest.mark.asyncio
async def test_send_does_not_raise_when_recipient_lookup_explodes(monkeypatch, sent):
    """Regression: this call was unguarded, so a failure here marked an
    already-committed ingestion run as failed in the admin UI."""
    payloads, _ = sent

    async def _boom():
        raise RuntimeError("clerk exploded")

    monkeypatch.setattr(email_mod, "get_summary_email_recipients", _boom)
    await send_ingestion_summary(SUMMARY)  # must not raise
    assert payloads == []


@pytest.mark.asyncio
async def test_send_does_not_raise_when_resend_fails(monkeypatch, sent):
    _, _ = sent

    def _boom(_payload):
        raise RuntimeError("resend down")

    monkeypatch.setattr(email_mod, "_send_sync", _boom)
    await send_ingestion_summary(SUMMARY)  # must not raise


@pytest.mark.asyncio
async def test_send_uses_one_email_per_recipient(monkeypatch, sent):
    """Recipients must not be exposed to each other via a shared `to` list."""
    payloads, _ = sent

    async def _three():
        return ["a@example.com", "b@example.com", "c@example.com"]

    monkeypatch.setattr(email_mod, "get_summary_email_recipients", _three)
    await send_ingestion_summary(SUMMARY)

    assert len(payloads) == 3
    assert [p["to"] for p in payloads] == [
        ["a@example.com"],
        ["b@example.com"],
        ["c@example.com"],
    ]
    assert all(len(p["to"]) == 1 for p in payloads)


@pytest.mark.asyncio
async def test_one_bad_address_does_not_block_the_rest(monkeypatch, sent):
    payloads, _ = sent

    async def _three():
        return ["good1@example.com", "bad@example.com", "good2@example.com"]

    def _selective(payload):
        if payload["to"] == ["bad@example.com"]:
            raise RuntimeError("invalid recipient")
        payloads.append(payload)
        return {"id": "ok"}

    monkeypatch.setattr(email_mod, "get_summary_email_recipients", _three)
    monkeypatch.setattr(email_mod, "_send_sync", _selective)
    await send_ingestion_summary(SUMMARY)

    assert [p["to"][0] for p in payloads] == ["good1@example.com", "good2@example.com"]
