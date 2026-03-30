from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery


ALLOWED_PRIVATE_SUFFIXES = (".local", ".internal", ".lan")


def is_intranet_webhook_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = parsed.hostname
        if not host:
            return False
        if host in {"localhost", "127.0.0.1", "::1"}:
            return True

        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            pass

        if host.endswith(ALLOWED_PRIVATE_SUFFIXES):
            return True

        if "." not in host:
            return True

        return False
    except Exception:
        return False


def generate_signature(secret: str, payload: dict, timestamp: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    msg = f"{timestamp}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def generate_idempotency_key(config_id: str, event_name: str, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    data = f"{config_id}:{event_name}:{body}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def queue_webhook_event(db: Session, event_name: str, payload: dict) -> list[WebhookDelivery]:
    configs = db.scalars(
        select(WebhookConfig).where(
            WebhookConfig.is_active.is_(True),
        )
    ).all()

    deliveries: list[WebhookDelivery] = []
    for cfg in configs:
        events = cfg.events or []
        if event_name not in events:
            continue

        if not is_intranet_webhook_url(cfg.url):
            continue

        key = generate_idempotency_key(str(cfg.id), event_name, payload)
        existing = db.scalar(select(WebhookDelivery).where(WebhookDelivery.idempotency_key == key))
        if existing:
            continue

        signature = None
        if cfg.secret:
            signature = generate_signature(cfg.secret, payload, datetime.now(timezone.utc).isoformat())

        delivery = WebhookDelivery(
            webhook_config_id=cfg.id,
            event_name=event_name,
            payload=payload,
            idempotency_key=key,
            signature=signature,
            status="queued",
            attempts=0,
        )
        db.add(delivery)
        db.flush()
        deliveries.append(delivery)

    return deliveries
