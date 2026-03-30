import enum


class RoleType(str, enum.Enum):
    STUDENT = "student"
    EMPLOYER_MANAGER = "employer_manager"
    CONTENT_AUTHOR = "content_author"
    REVIEWER = "reviewer"
    SYSTEM_ADMINISTRATOR = "system_administrator"


class ContentType(str, enum.Enum):
    ARTICLE = "article"
    VIDEO = "video"
    JOB_ANNOUNCEMENT = "job_announcement"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    RETRACTED = "retracted"


class ReviewDecisionType(str, enum.Enum):
    APPROVE = "approve"
    RETURN_FOR_REVISION = "return_for_revision"
    REJECT = "reject"


class SegmentationType(str, enum.Enum):
    RANDOM = "random"
    COHORT = "cohort"
    ROLE = "role"
    USER_LIST = "user_list"


class AnnotationVisibility(str, enum.Enum):
    PRIVATE = "private"
    COHORT = "cohort"
    PUBLIC = "public"


class EventType(str, enum.Enum):
    PLAY = "play"
    SKIP = "skip"
    FAVORITE = "favorite"
    SEARCH = "search"
    JOB_APPLICATION = "job_application"
    APPLICATION = "application"
    VIEW = "view"
    DOWNLOAD = "download"
    SHARE = "share"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"


class WebhookEvent(str, enum.Enum):
    CONTENT_PUBLISHED = "content.published"
    CONTENT_RETRACTED = "content.retracted"
    APPLICATION_SUBMITTED = "application.submitted"
    APPLICATION_STATUS_CHANGED = "application.status_changed"
    USER_REGISTERED = "user.registered"
    REVIEW_COMPLETED = "review.completed"
