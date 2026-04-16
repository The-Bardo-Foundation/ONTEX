"""
Clerk JWT verification middleware for FastAPI.

Uses python-jose + httpx to verify Clerk-issued JWTs against the Clerk JWKS
endpoint.  JWKS are cached for 1 hour to avoid fetching on every request.

Usage:
    from app.api.middleware import clerk_user

    @router.patch("/trials/{nct_id}/approve")
    async def approve_trial(
        nct_id: str,
        body: ApproveBody,
        user: dict = Depends(clerk_user),
        db: AsyncSession = Depends(get_db),
    ):
        username = user.get("email") or user.get("sub", "admin")
        ...
"""

import os
import time
from typing import Any, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)

# ── JWKS cache ────────────────────────────────────────────────────────────────
_jwks_cache: Optional[dict] = None
_jwks_cached_at: float = 0.0
_JWKS_TTL = 3600  # seconds


def _derive_jwks_url(publishable_key: str) -> str:
    """
    Derive the Clerk JWKS endpoint URL from the publishable key.

    Clerk publishable keys are formatted as:
        pk_test_<base64url(domain + "$")>
        pk_live_<base64url(domain + "$")>

    We strip the prefix, base64-decode the payload, strip the trailing "$"
    and build the JWKS URL from the domain.
    """
    import base64

    try:
        payload = publishable_key.split("_", 2)[-1]  # e.g. bm90YWJs...
        # base64url decode (add padding if needed)
        padded = payload + "=" * (-len(payload) % 4)
        domain = base64.urlsafe_b64decode(padded).decode("utf-8").rstrip("$")
        return f"https://{domain}/.well-known/jwks.json"
    except Exception:
        # Fallback: check settings
        return getattr(settings, "CLERK_JWKS_URL", "")


_JWKS_URL = _derive_jwks_url(
    getattr(settings, "CLERK_PUBLISHABLE_KEY", "")
    or "pk_test_bm90YWJsZS1yaGluby03Ni5jbGVyay5hY2NvdW50cy5kZXYk"
)


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_cached_at

    if _jwks_cache and (time.monotonic() - _jwks_cached_at) < _JWKS_TTL:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(_JWKS_URL, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cached_at = time.monotonic()
        return _jwks_cache


async def clerk_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict[str, Any]:
    """
    FastAPI dependency that validates a Clerk Bearer JWT and returns the claims.

    JWT verification is skipped only when SKIP_AUTH_FOR_TESTS=1 is explicitly
    set (test runner only).  Never set this in production.
    Raises HTTP 401 if the token is missing or invalid in all other cases.
    """
    if os.getenv("SKIP_AUTH_FOR_TESTS") == "1":
        # Skip verification; return stub claims so tests pass unchanged.
        return {"sub": "local-admin", "email": "admin@local"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        jwks = await _get_jwks()
        # Decode without verification first to get the kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Find the matching key in JWKS
        key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid),
            None,
        )
        if key is None:
            # kid not found — refresh JWKS once and retry
            global _jwks_cached_at
            _jwks_cached_at = 0.0
            jwks = await _get_jwks()
            key = next(
                (k for k in jwks.get("keys", []) if k.get("kid") == kid),
                None,
            )

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown signing key",
            )

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        # Normalise: extract a useful "email" field from Clerk's primary_email_address
        # claim or the standard email claim if present.
        if "email" not in claims:
            claims["email"] = claims.get("primary_email_address_id") or claims.get("sub")

        return claims

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
