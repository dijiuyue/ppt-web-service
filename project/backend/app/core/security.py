"""Security utilities for the PPT Master Web Service.

Provides simple API-key based authentication suitable for
service-to-service calls and development environments.
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# ---------------------------------------------------------------------------
# API Key authentication
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify the ``X-API-Key`` header against the configured secret.

    If ``SECURITY_API_KEY`` is not configured, authentication is bypassed
    (useful during local development).
    """
    expected = settings.security.api_key

    # If no API key is configured, allow all requests (dev mode)
    if expected is None:
        return "dev"

    if api_key is None or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure random API key."""
    return secrets.token_urlsafe(length)
