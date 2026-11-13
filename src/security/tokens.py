import secrets
import enum
from datetime import datetime, timedelta, timezone

import jwt

from config.settings import settings
from exceptions.accounts import InvalidJWTToken, ExpiredJWTToken


class JWTTokenTypes(enum.StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def generate_regular_token(length=32):
    return secrets.token_urlsafe(length)


def generate_jwt_token(user_id: int, token_type: JWTTokenTypes, lifetime: timedelta):
    the_now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id),
        "type": token_type,
        "iat": the_now,
        "exp": the_now + lifetime,
        "jti": secrets.token_hex(8)  # to prevent same second duplicate
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int):
    return generate_jwt_token(
        user_id, JWTTokenTypes.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: int):
    return generate_jwt_token(
        user_id, JWTTokenTypes.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_jwt_token(token: str, expected_type: JWTTokenTypes):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["user_id", "type", "exp"]}
        )
    except jwt.ExpiredSignatureError:
        raise ExpiredJWTToken("Token expired")
    except jwt.InvalidTokenError:
        raise InvalidJWTToken("Invalid token")
    if payload["type"] != expected_type:
        raise InvalidJWTToken("Invalid token type")
    return payload
