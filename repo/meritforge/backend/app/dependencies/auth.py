from typing import Callable
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.enums import RoleType
from app.core.security import decode_token, verify_password
from app.models.user import User


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=settings.access_cookie_name),
) -> User:
    if not access_token:
        raise _unauthorized()

    try:
        payload = decode_token(access_token)
    except ValueError as exc:
        raise _unauthorized("Invalid access token") from exc

    if payload.get("type") != "access":
        raise _unauthorized("Invalid access token type")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Malformed access token")

    user = db.scalar(select(User).where(User.id == UUID(user_id)))
    if not user or not user.is_active:
        raise _unauthorized("Inactive or missing user")

    return user


def require_roles(*required_roles: RoleType | str) -> Callable:
    normalized = {r.value if isinstance(r, RoleType) else str(r) for r in required_roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role = None
        if current_user.role is not None:
            user_role = current_user.role.name.value if hasattr(current_user.role.name, "value") else str(current_user.role.name)

        if user_role not in normalized:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return current_user

    return dependency


def require_step_up_confirmation(
    current_user: User = Depends(get_current_user),
    step_up_password: str | None = Header(default=None, alias=settings.step_up_header_name),
) -> User:
    if not step_up_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Step-up confirmation required: provide password in X-Step-Up-Password header",
        )

    if not verify_password(step_up_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid step-up credentials")

    return current_user


def require_step_up_for_permission_changes(
    user: User = Depends(require_step_up_confirmation),
) -> User:
    return user


def require_step_up_for_takedowns(
    user: User = Depends(require_step_up_confirmation),
) -> User:
    return user


def require_step_up_for_account_deletion(
    user: User = Depends(require_step_up_confirmation),
) -> User:
    return user
