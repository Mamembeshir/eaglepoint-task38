from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.models.audit_log import AuditLog
from app.models.user import User


REDACTED_VALUE = "[REDACTED]"
# Redact common sensitive keys from audit payloads before persistence.
# Covered fields include passwords, refresh/access tokens, webhook/integration secrets,
# and authorization-style headers/keys.
SENSITIVE_KEYS = {
    "password",
    "new_password",
    "current_password",
    "hashed_password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "secret",
    "webhook_secret",
    "signature",
    "x-webhook-signature",
    "x-meritforge-signature",
}


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in SENSITIVE_KEYS or normalized_key.endswith("_token") or normalized_key.endswith("_secret"):
                sanitized[key] = REDACTED_VALUE
            else:
                sanitized[key] = _redact_sensitive(nested_value)
        return sanitized
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_sensitive(item) for item in value)
    return value


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool, list, dict)):
        return value
    return str(value)


def _json_diff(before_data: Any, after_data: Any) -> dict | None:
    if not isinstance(before_data, dict) or not isinstance(after_data, dict):
        return None

    changed: dict[str, dict[str, Any]] = {}
    keys = set(before_data.keys()).union(after_data.keys())
    for key in sorted(keys):
        before_val = before_data.get(key)
        after_val = after_data.get(key)
        if before_val != after_val:
            changed[key] = {"before": _normalize(before_val), "after": _normalize(after_val)}
    return changed if changed else None


def write_audit_log(
    db: Session,
    *,
    action: AuditAction,
    entity_type: str,
    entity_id: str | None,
    actor: User | None,
    request: Request | None,
    before_data: Any = None,
    after_data: Any = None,
    changes: Any = None,
    description: str | None = None,
) -> None:
    normalized_before = _normalize(_redact_sensitive(before_data))
    normalized_after = _normalize(_redact_sensitive(after_data))
    normalized_changes = _normalize(_redact_sensitive(changes))
    computed_diff = _json_diff(normalized_before, normalized_after)

    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=actor.id if actor else None,
        user_email=actor.email if actor else None,
        ip_address=(request.client.host if request and request.client else None),
        user_agent=(request.headers.get("user-agent") if request else None),
        before_data=normalized_before,
        after_data=normalized_after,
        changes=normalized_changes if normalized_changes is not None else computed_diff,
        description=description,
        request_url=(str(request.url) if request else None),
        request_method=(request.method if request else None),
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
