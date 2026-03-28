from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TopicSubscriptionCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=100)


class TopicSubscriptionOut(BaseModel):
    id: UUID
    topic: str
    created_at: datetime
