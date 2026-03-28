from datetime import date

from pydantic import BaseModel, Field


class OperationsMetricsQuery(BaseModel):
    start_date: date
    end_date: date


class RetentionMetricsOut(BaseModel):
    active_users: int
    returning_users: int
    retention_percentage: float


class ConversionMetricsOut(BaseModel):
    interacted_users: int
    applying_users: int
    converted_users: int
    conversion_percentage: float


class FunnelMetricsOut(BaseModel):
    job_posts: int
    applications: int
    milestone_completions: int
    post_to_application_percentage: float
    application_to_milestone_percentage: float


class EventTrendPointOut(BaseModel):
    metric_date: date
    event_type: str
    event_count: int
    unique_user_count: int


class EventTrendSummaryOut(BaseModel):
    event_type: str
    current_total: int
    previous_total: int
    trend_delta: int
    trend_percentage: float


class OperationsDashboardOut(BaseModel):
    start_date: date
    end_date: date
    retention: RetentionMetricsOut
    conversion: ConversionMetricsOut
    funnel: FunnelMetricsOut
    trend_summaries: list[EventTrendSummaryOut]
