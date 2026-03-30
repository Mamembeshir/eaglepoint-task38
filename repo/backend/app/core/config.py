import os


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_key_map(value: str | None) -> dict[str, str]:
    entries = _parse_csv(value)
    key_map: dict[str, str] = {}
    for entry in entries:
        if ":" not in entry:
            continue
        key_id, secret = entry.split(":", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            key_map[key_id] = secret
    return key_map


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    password_pepper_current: str = os.getenv("PASSWORD_PEPPER_CURRENT", "")
    password_pepper_previous: list[str] = _parse_csv(os.getenv("PASSWORD_PEPPER_PREVIOUS"))
    refresh_token_hash_keys: dict[str, str] = _parse_key_map(os.getenv("REFRESH_TOKEN_HASH_KEYS"))
    refresh_token_hash_active_key_id: str = os.getenv("REFRESH_TOKEN_HASH_ACTIVE_KEY_ID", "legacy-sha256")
    refresh_token_hash_rotation_days: int = int(os.getenv("REFRESH_TOKEN_HASH_ROTATION_DAYS", "180"))
    allow_registration: bool = _parse_bool(os.getenv("ALLOW_REGISTRATION"), True)
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "true").lower() == "true"
    cookie_domain: str | None = os.getenv("COOKIE_DOMAIN")
    access_cookie_name: str = os.getenv("ACCESS_COOKIE_NAME", "access_token")
    refresh_cookie_name: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    step_up_cookie_name: str = os.getenv("STEP_UP_COOKIE_NAME", "step_up_token")
    step_up_expire_minutes: int = int(os.getenv("STEP_UP_EXPIRE_MINUTES", "5"))
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    user_rate_limit_per_minute: int = int(os.getenv("USER_RATE_LIMIT_PER_MINUTE", "120"))
    rate_limit_fail_closed: bool = _parse_bool(os.getenv("RATE_LIMIT_FAIL_CLOSED"), False)
    idempotency_fail_closed: bool = _parse_bool(os.getenv("IDEMPOTENCY_FAIL_CLOSED"), False)
    integration_hmac_keys: dict[str, str] = _parse_key_map(os.getenv("INTEGRATION_HMAC_KEYS"))
    integration_hmac_timestamp_header: str = os.getenv("INTEGRATION_HMAC_TIMESTAMP_HEADER", "X-MeritForge-Timestamp")
    integration_hmac_signature_header: str = os.getenv("INTEGRATION_HMAC_SIGNATURE_HEADER", "X-MeritForge-Signature")
    integration_hmac_key_id_header: str = os.getenv("INTEGRATION_HMAC_KEY_ID_HEADER", "X-MeritForge-Key-Id")
    integration_hmac_clock_skew_seconds: int = int(os.getenv("INTEGRATION_HMAC_CLOCK_SKEW_SECONDS", "300"))
    cors_origins: list[str] = _parse_csv(os.getenv("CORS_ORIGINS", "https://localhost,http://localhost:3000"))


settings = Settings()
