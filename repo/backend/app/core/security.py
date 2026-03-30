from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
LEGACY_TOKEN_HASH_KEY_ID = "legacy-sha256"


def _password_candidates(plain_password: str) -> list[str]:
    peppers = [settings.password_pepper_current, *settings.password_pepper_previous, ""]
    candidates: list[str] = []
    for pepper in peppers:
        candidate = f"{plain_password}{pepper}"
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def verify_password(plain_password: str, hashed_password: str) -> bool:
    for candidate in _password_candidates(plain_password):
        if pwd_context.verify(candidate, hashed_password):
            return True
    return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(f"{password}{settings.password_pepper_current}")


def _legacy_hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hmac_hash_token(raw_token: str, key: str) -> str:
    return hmac.new(key.encode("utf-8"), raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_token(raw_token: str) -> tuple[str, str]:
    key_id = settings.refresh_token_hash_active_key_id
    key = settings.refresh_token_hash_keys.get(key_id)
    if key:
        return key_id, _hmac_hash_token(raw_token, key)
    return LEGACY_TOKEN_HASH_KEY_ID, _legacy_hash_token(raw_token)


def verify_token_hash(raw_token: str, stored_hash: str, key_id: str | None) -> bool:
    if key_id and key_id != LEGACY_TOKEN_HASH_KEY_ID:
        key = settings.refresh_token_hash_keys.get(key_id)
        if not key:
            return False
        return hmac.compare_digest(stored_hash, _hmac_hash_token(raw_token, key))
    return hmac.compare_digest(stored_hash, _legacy_hash_token(raw_token))


def _create_token(subject: str, token_type: str, expires_delta: timedelta, role: str | None = None) -> tuple[str, str, datetime]:
    expire = datetime.now(timezone.utc) + expires_delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if role:
        payload["role"] = role
    encoded_jwt = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt, jti, expire


def create_access_token(subject: str, role: str | None = None) -> tuple[str, str, datetime]:
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
    )


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def create_step_up_token(subject: str) -> tuple[str, str, datetime]:
    return _create_token(
        subject=subject,
        token_type="step_up",
        expires_delta=timedelta(minutes=settings.step_up_expire_minutes),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
