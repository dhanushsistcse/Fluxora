"""Minimal structured audit events that deliberately exclude request bodies/secrets."""

from __future__ import annotations

import logging


_logger = logging.getLogger("fluxora.audit")


def audit_event(event: str, **fields: object) -> None:
    sensitive_terms = ("authorization", "token", "password", "content", "secret", "body")
    safe_fields = {
        key: value
        for key, value in fields.items()
        if not any(term in key.lower() for term in sensitive_terms)
    }
    _logger.info(event, extra={"audit_event": event, **safe_fields})
