from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.user_topic_subscription import UserTopicSubscription
from app.schemas.topic_subscriptions import TopicSubscriptionCreateRequest, TopicSubscriptionOut

router = APIRouter(tags=["Topic Subscriptions"])


def _normalize_topic(topic: str) -> str:
    return topic.strip().lower()


@router.get("/users/me/topic-subscriptions", response_model=list[TopicSubscriptionOut])
def list_my_topic_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicSubscriptionOut]:
    rows = db.scalars(
        select(UserTopicSubscription)
        .where(UserTopicSubscription.user_id == current_user.id)
        .order_by(UserTopicSubscription.created_at.desc())
    ).all()
    return [TopicSubscriptionOut(id=row.id, topic=row.topic, created_at=row.created_at) for row in rows]


@router.post("/users/me/topic-subscriptions", response_model=TopicSubscriptionOut, status_code=status.HTTP_201_CREATED)
def subscribe_topic(
    payload: TopicSubscriptionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicSubscriptionOut:
    normalized_topic = _normalize_topic(payload.topic)
    if not normalized_topic:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Topic cannot be empty")

    existing = db.scalar(
        select(UserTopicSubscription).where(
            UserTopicSubscription.user_id == current_user.id,
            UserTopicSubscription.topic == normalized_topic,
        )
    )
    if existing:
        return TopicSubscriptionOut(id=existing.id, topic=existing.topic, created_at=existing.created_at)

    row = UserTopicSubscription(user_id=current_user.id, topic=normalized_topic)
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="topic_subscription",
        entity_id=str(row.id),
        actor=current_user,
        request=request,
        after_data={"topic": row.topic},
        description="Subscribed to topic",
    )
    db.commit()
    db.refresh(row)
    return TopicSubscriptionOut(id=row.id, topic=row.topic, created_at=row.created_at)


@router.delete("/users/me/topic-subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_topic(
    request: Request,
    topic: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    normalized_topic = _normalize_topic(topic)
    row = db.scalar(
        select(UserTopicSubscription).where(
            UserTopicSubscription.user_id == current_user.id,
            UserTopicSubscription.topic == normalized_topic,
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic subscription not found")

    write_audit_log(
        db,
        action=AuditAction.DELETE,
        entity_type="topic_subscription",
        entity_id=str(row.id),
        actor=current_user,
        request=request,
        before_data={"topic": row.topic},
        description="Unsubscribed from topic",
    )
    db.delete(row)
    db.commit()
