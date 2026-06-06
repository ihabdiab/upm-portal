"""Password hashing (bcrypt) and JWT access/refresh tokens (§11.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from upm_backend.config import get_settings


def hash_password(plain: str) -> str:
    # bcrypt caps at 72 bytes; truncate defensively to avoid backend-specific errors.
    pw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _encode(sub: str, token_type: str, ttl: timedelta) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def create_access_token(user_id: int) -> str:
    s = get_settings()
    return _encode(str(user_id), "access", timedelta(minutes=s.access_ttl_min))


def create_refresh_token(user_id: int) -> str:
    s = get_settings()
    return _encode(str(user_id), "refresh", timedelta(days=s.refresh_ttl_days))


def decode_token(token: str, *, expected_type: str | None = None) -> dict:
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload
