from datetime import datetime, timezone
import hashlib
import hmac
import json

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import settings


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_key_id(header_key_id: str | None) -> str:
    if header_key_id:
        return header_key_id

    configured = settings.integration_hmac_keys
    if len(configured) == 1:
        return next(iter(configured.keys()))

    raise _unauthorized("Missing integration key id")


async def verify_integration_hmac(
    request: Request,
    timestamp: str | None = Header(default=None, alias=settings.integration_hmac_timestamp_header),
    signature: str | None = Header(default=None, alias=settings.integration_hmac_signature_header),
    key_id: str | None = Header(default=None, alias=settings.integration_hmac_key_id_header),
) -> dict[str, str]:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE", "GET"}:
        raise _unauthorized("Unsupported integration method")

    if not timestamp or not signature:
        raise _unauthorized("Missing integration signature headers")

    if not settings.integration_hmac_keys:
        raise _unauthorized("Integration HMAC keys are not configured")

    try:
        request_ts = _parse_timestamp(timestamp)
    except Exception as exc:
        raise _unauthorized("Invalid timestamp format") from exc

    now = datetime.now(timezone.utc)
    skew = abs((now - request_ts).total_seconds())
    if skew > settings.integration_hmac_clock_skew_seconds:
        raise _unauthorized("Stale integration timestamp")

    resolved_key_id = _resolve_key_id(key_id)
    secret = settings.integration_hmac_keys.get(resolved_key_id)
    if not secret:
        raise _unauthorized("Invalid integration key id")

    raw_body = await request.body()

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:
        raise _unauthorized("Invalid integration payload") from exc

    canonical_body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    # String-to-sign format mirrors outbound webhooks: "<timestamp>.<canonical_json_body>"
    string_to_sign = f"{timestamp}.{canonical_body}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise _unauthorized("Invalid integration signature")

    return {"key_id": resolved_key_id}


def require_integration_hmac(auth: dict[str, str] = Depends(verify_integration_hmac)) -> dict[str, str]:
    return auth
