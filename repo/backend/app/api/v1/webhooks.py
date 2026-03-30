from datetime import datetime, timezone
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, RoleType
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User
from app.models.webhook_dead_letter import WebhookDeadLetter
from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery
from app.schemas.webhooks import (
    WebhookConfigCreateRequest,
    WebhookConfigOut,
    WebhookDeliveryOut,
    WebhookDispatchOut,
    WebhookDispatchRequest,
    WebhookRetryOut,
)
from app.services.webhook_service import generate_signature, is_intranet_webhook_url, queue_webhook_event

router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks/configs", response_model=WebhookConfigOut, status_code=status.HTTP_201_CREATED)
def create_webhook_config(
    payload: WebhookConfigCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> WebhookConfigOut:
    if not is_intranet_webhook_url(str(payload.url)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Public internet webhooks are not allowed")

    config = WebhookConfig(
        name=payload.name,
        url=str(payload.url),
        secret=payload.secret,
        events=payload.events,
        headers=payload.headers,
        retry_count=payload.retry_count,
        retry_delay_seconds=payload.retry_delay_seconds,
        timeout_seconds=payload.timeout_seconds,
        created_by_id=current_user.id,
    )
    db.add(config)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="webhook_config",
        entity_id=str(config.id),
        actor=current_user,
        request=request,
        after_data={"url": config.url, "events": config.events},
        description="Created intranet webhook config",
    )
    db.commit()

    return WebhookConfigOut(
        id=config.id,
        name=config.name,
        url=config.url,
        events=config.events,
        is_active=config.is_active,
        retry_count=config.retry_count,
        retry_delay_seconds=config.retry_delay_seconds,
        timeout_seconds=config.timeout_seconds,
        created_by_id=config.created_by_id,
        created_at=config.created_at,
    )


@router.get("/webhooks/configs", response_model=list[WebhookConfigOut])
def list_webhook_configs(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> list[WebhookConfigOut]:
    configs = db.scalars(select(WebhookConfig).order_by(WebhookConfig.created_at.desc())).all()
    return [
        WebhookConfigOut(
            id=c.id,
            name=c.name,
            url=c.url,
            events=c.events,
            is_active=c.is_active,
            retry_count=c.retry_count,
            retry_delay_seconds=c.retry_delay_seconds,
            timeout_seconds=c.timeout_seconds,
            created_by_id=c.created_by_id,
            created_at=c.created_at,
        )
        for c in configs
    ]


@router.post("/webhooks/dispatch", response_model=WebhookDispatchOut)
def dispatch_webhook_event(
    payload: WebhookDispatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> WebhookDispatchOut:
    deliveries = queue_webhook_event(db, payload.event_name, payload.payload)

    from app.tasks.webhook_tasks import deliver_webhook

    for d in deliveries:
        deliver_webhook.delay(str(d.id))

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="webhook_dispatch",
        entity_id=None,
        actor=current_user,
        request=request,
        after_data={"event_name": payload.event_name, "queued_deliveries": len(deliveries)},
        description="Queued webhook deliveries",
    )
    db.commit()

    return WebhookDispatchOut(queued_deliveries=len(deliveries), delivery_ids=[d.id for d in deliveries])


@router.get("/webhooks/deliveries", response_model=list[WebhookDeliveryOut])
def list_webhook_deliveries(
    status_filter: str | None = Query(default=None, alias="status"),
    webhook_config_id: uuid.UUID | None = Query(default=None),
    event_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> list[WebhookDeliveryOut]:
    query = select(WebhookDelivery)
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)
    if webhook_config_id:
        query = query.where(WebhookDelivery.webhook_config_id == webhook_config_id)
    if event_name:
        query = query.where(WebhookDelivery.event_name == event_name)

    rows = db.scalars(query.order_by(WebhookDelivery.created_at.desc()).limit(limit)).all()
    return [
        WebhookDeliveryOut(
            id=row.id,
            webhook_config_id=row.webhook_config_id,
            event_name=row.event_name,
            status=row.status,
            attempts=row.attempts,
            response_status=row.response_status,
            last_error=row.last_error,
            queued_at=row.queued_at,
            delivered_at=row.delivered_at,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/webhooks/deliveries/{delivery_id}/retry", response_model=WebhookRetryOut)
def retry_webhook_delivery(
    delivery_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> WebhookRetryOut:
    original = db.scalar(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook delivery not found")
    if original.status == "success":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Successful delivery cannot be retried")

    config = db.scalar(select(WebhookConfig).where(WebhookConfig.id == original.webhook_config_id))
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook config not found")
    if not config.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Webhook config is inactive")
    if not is_intranet_webhook_url(config.url):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Public internet webhooks are not allowed")

    retry_key = hashlib.sha256(f"{original.idempotency_key}:{datetime.now(timezone.utc).isoformat()}".encode("utf-8")).hexdigest()
    retried = WebhookDelivery(
        webhook_config_id=original.webhook_config_id,
        event_name=original.event_name,
        payload=original.payload,
        idempotency_key=retry_key,
        signature=generate_signature(config.secret, original.payload, datetime.now(timezone.utc).isoformat()) if config.secret else None,
        status="queued",
        attempts=0,
        response_status=None,
        last_error=None,
    )
    db.add(retried)
    db.flush()

    dead_letter = db.scalar(select(WebhookDeadLetter).where(WebhookDeadLetter.delivery_id == original.id))
    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="webhook_delivery_retry",
        entity_id=str(retried.id),
        actor=current_user,
        request=request,
        before_data={
            "original_delivery_id": str(original.id),
            "original_status": original.status,
            "dead_letter_exists": bool(dead_letter),
        },
        after_data={
            "retried_delivery_id": str(retried.id),
            "status": retried.status,
        },
        description="Retried webhook delivery",
    )
    db.commit()

    from app.tasks.webhook_tasks import deliver_webhook

    deliver_webhook.delay(str(retried.id))

    return WebhookRetryOut(
        original_delivery_id=original.id,
        retried_delivery_id=retried.id,
        status="queued",
    )
