from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.webhook_config import WebhookConfig
from app.models.webhook_dead_letter import WebhookDeadLetter
from app.models.webhook_delivery import WebhookDelivery
from app.services.webhook_service import generate_signature, is_intranet_webhook_url


@celery_app.task(name="app.tasks.webhook_tasks.deliver_webhook")
def deliver_webhook(delivery_id: str) -> dict:
    db = SessionLocal()
    try:
        delivery = db.scalar(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
        if not delivery:
            return {"status": "missing_delivery"}
        if delivery.status in {"success", "dead_letter"}:
            return {"status": delivery.status}

        config = db.scalar(select(WebhookConfig).where(WebhookConfig.id == delivery.webhook_config_id))
        if not config or not config.is_active:
            delivery.status = "dead_letter"
            delivery.last_error = "webhook config missing or inactive"
            db.add(
                WebhookDeadLetter(
                    delivery_id=delivery.id,
                    webhook_config_id=delivery.webhook_config_id,
                    event_name=delivery.event_name,
                    payload=delivery.payload,
                    error_message=delivery.last_error,
                )
            )
            db.commit()
            return {"status": "dead_letter"}

        if not is_intranet_webhook_url(config.url):
            delivery.status = "dead_letter"
            delivery.last_error = "public internet webhook blocked"
            db.add(
                WebhookDeadLetter(
                    delivery_id=delivery.id,
                    webhook_config_id=delivery.webhook_config_id,
                    event_name=delivery.event_name,
                    payload=delivery.payload,
                    error_message=delivery.last_error,
                )
            )
            db.commit()
            return {"status": "dead_letter"}

        timestamp = datetime.now(timezone.utc).isoformat()
        headers = {"Content-Type": "application/json", "X-Idempotency-Key": delivery.idempotency_key, "X-Webhook-Timestamp": timestamp}
        if config.headers:
            headers.update(config.headers)
        if config.secret:
            signature = generate_signature(config.secret, delivery.payload, timestamp)
            headers["X-Webhook-Signature"] = signature
            delivery.signature = signature

        delivery.attempts += 1

        try:
            with httpx.Client(timeout=float(config.timeout_seconds)) as client:
                response = client.post(config.url, json=delivery.payload, headers=headers)
            delivery.response_status = response.status_code

            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.now(timezone.utc)
                config.last_success_at = delivery.delivered_at
                config.success_count += 1
                config.last_triggered_at = delivery.delivered_at
                db.commit()
                return {"status": "success", "status_code": response.status_code}

            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as exc:
            delivery.last_error = str(exc)
            config.last_failure_at = datetime.now(timezone.utc)
            config.failure_count += 1
            config.last_error = delivery.last_error
            config.last_response_status = delivery.response_status

            if delivery.attempts <= max(0, int(config.retry_count)):
                delivery.status = "retrying"
                db.commit()
                countdown = max(1, int(config.retry_delay_seconds))
                deliver_webhook.apply_async(args=[delivery_id], countdown=countdown)
                return {"status": "retrying", "attempts": delivery.attempts}

            delivery.status = "dead_letter"
            db.add(
                WebhookDeadLetter(
                    delivery_id=delivery.id,
                    webhook_config_id=delivery.webhook_config_id,
                    event_name=delivery.event_name,
                    payload=delivery.payload,
                    error_message=delivery.last_error or "delivery failed",
                )
            )
            db.commit()
            return {"status": "dead_letter", "attempts": delivery.attempts}
    finally:
        db.close()
