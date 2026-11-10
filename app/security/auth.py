"""Fail-closed bearer-token authentication for the starter API."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Header, HTTPException, Request

from app.security.audit import audit_event
from app.security.rate_limit import limiter


def require_principal(request: Request, authorization: str | None = Header(default=None)) -> str:
    expected = os.environ.get("FLUXORA_API_TOKEN", "")
    if not expected:
        audit_event("authentication_unconfigured")
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        audit_event("authentication_rejected")
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    principal = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    request.state.principal = principal
    if not limiter.allow(principal):
        audit_event("rate_limit_exceeded", principal_id=principal)
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    audit_event("authentication_accepted", principal_id=principal)
    return principal
