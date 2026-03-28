from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.database import get_db
from app.core.enums import AuditAction, RoleType
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    verify_token_hash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, LogoutResponse, RegisterRequest, UserAuthOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, access_exp: datetime, refresh_exp: datetime) -> None:
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        expires=int(access_exp.timestamp()),
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        expires=int(refresh_exp.timestamp()),
        path="/api/v1/auth",
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(settings.refresh_cookie_name, path="/api/v1/auth", domain=settings.cookie_domain)


def _issue_and_store_tokens(db: Session, user: User) -> tuple[str, str, datetime, datetime]:
    role_value = None
    if user.role is not None:
        role_value = user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)

    access_token, _, access_exp = create_access_token(subject=str(user.id), role=role_value)
    refresh_token, refresh_jti, refresh_exp = create_refresh_token(subject=str(user.id))

    refresh_key_id, refresh_hash = hash_token(refresh_token)
    refresh_record = RefreshToken(
        user_id=user.id,
        token_jti=refresh_jti,
        token_hash=refresh_hash,
        token_hash_key_id=refresh_key_id,
        expires_at=refresh_exp,
    )
    db.add(refresh_record)
    db.commit()

    return access_token, refresh_token, access_exp, refresh_exp


def _user_auth_out(user: User) -> UserAuthOut:
    role_value = None
    if user.role is not None:
        role_value = user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)

    return UserAuthOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        role=role_value,
        created_at=user.created_at,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    student_role = db.scalar(select(Role).where(Role.name == RoleType.STUDENT.value))
    if not student_role:
        student_role = db.scalar(select(Role).where(Role.name == RoleType.STUDENT))
    if not student_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role is missing")

    user = User(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        display_name=payload.display_name,
        role_id=student_role.id,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token, refresh_token, access_exp, refresh_exp = _issue_and_store_tokens(db, user)
    _set_auth_cookies(response, access_token, refresh_token, access_exp, refresh_exp)

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="auth_register",
        entity_id=str(user.id),
        actor=user,
        request=request,
        after_data={"email": user.email, "role_id": user.role_id},
        description="User registered",
    )
    db.commit()

    return AuthResponse(user=_user_auth_out(user), access_token_expires_at=access_exp, refresh_token_expires_at=refresh_exp)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token, refresh_token, access_exp, refresh_exp = _issue_and_store_tokens(db, user)
    _set_auth_cookies(response, access_token, refresh_token, access_exp, refresh_exp)

    write_audit_log(
        db,
        action=AuditAction.LOGIN,
        entity_type="auth_login",
        entity_id=str(user.id),
        actor=user,
        request=request,
        after_data={"email": user.email},
        description="User login",
    )
    db.commit()

    return AuthResponse(user=_user_auth_out(user), access_token_expires_at=access_exp, refresh_token_expires_at=refresh_exp)


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = decode_token(raw_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    token_jti = payload.get("jti")
    if not user_id or not token_jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token")

    refresh_record = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == token_jti))
    if not refresh_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not recognized")
    if refresh_record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    if refresh_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    if not verify_token_hash(raw_refresh, refresh_record.token_hash, refresh_record.token_hash_key_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token mismatch")
    if str(refresh_record.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token owner mismatch")

    user = db.scalar(select(User).where(User.id == UUID(user_id)))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User invalid or inactive")

    refresh_record.revoked_at = datetime.now(timezone.utc)
    refresh_record.last_used_at = datetime.now(timezone.utc)

    role_value = None
    if user.role is not None:
        role_value = user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)
    access_token, _, access_exp = create_access_token(subject=str(user.id), role=role_value)
    new_refresh_token, new_jti, refresh_exp = create_refresh_token(subject=str(user.id))
    new_refresh_key_id, new_refresh_hash = hash_token(new_refresh_token)
    new_record = RefreshToken(
        user_id=user.id,
        token_jti=new_jti,
        token_hash=new_refresh_hash,
        token_hash_key_id=new_refresh_key_id,
        expires_at=refresh_exp,
    )
    db.add(new_record)
    db.flush()
    refresh_record.replaced_by_token_id = new_record.id

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="auth_refresh",
        entity_id=str(user.id),
        actor=user,
        request=request,
        before_data={"refresh_token_jti": refresh_record.token_jti},
        after_data={"refresh_token_jti": new_record.token_jti},
        description="Refresh token rotated",
    )
    db.commit()

    _set_auth_cookies(response, access_token, new_refresh_token, access_exp, refresh_exp)
    return AuthResponse(user=_user_auth_out(user), access_token_expires_at=access_exp, refresh_token_expires_at=refresh_exp)


@router.post("/logout", response_model=LogoutResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> LogoutResponse:
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh:
        try:
            payload = decode_token(raw_refresh)
            token_jti = payload.get("jti")
            if token_jti:
                refresh_record = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == token_jti))
                if refresh_record and refresh_record.revoked_at is None:
                    refresh_record.revoked_at = datetime.now(timezone.utc)
                    refresh_record.last_used_at = datetime.now(timezone.utc)
                    user = db.scalar(select(User).where(User.id == refresh_record.user_id))
                    write_audit_log(
                        db,
                        action=AuditAction.LOGOUT,
                        entity_type="auth_logout",
                        entity_id=str(refresh_record.user_id),
                        actor=user,
                        request=request,
                        before_data={"refresh_token_jti": refresh_record.token_jti, "revoked_at": None},
                        after_data={"refresh_token_jti": refresh_record.token_jti, "revoked_at": refresh_record.revoked_at.isoformat()},
                        description="User logout",
                    )
                    db.commit()
        except ValueError:
            pass

    _clear_auth_cookies(response)
    return LogoutResponse(message="Logged out successfully")
