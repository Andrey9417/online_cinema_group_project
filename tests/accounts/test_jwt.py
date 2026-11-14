from datetime import timedelta

import jwt
import pytest

from config.settings import settings
from exceptions.accounts import ExpiredJWTToken, InvalidJWTToken
from security.tokens import (
    JWTTokenTypes,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    generate_jwt_token,
)


def test_access_token_round_trip():
    payload = decode_jwt_token(create_access_token(42), JWTTokenTypes.ACCESS)

    assert payload["user_id"] == "42"
    assert payload["type"] == JWTTokenTypes.ACCESS
    assert payload["exp"] - payload["iat"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert payload["jti"]


def test_refresh_token_round_trip():
    payload = decode_jwt_token(create_refresh_token(42), JWTTokenTypes.REFRESH)

    assert payload["user_id"] == "42"
    assert payload["type"] == JWTTokenTypes.REFRESH
    assert payload["exp"] - payload["iat"] == settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def test_tokens_created_in_the_same_second_are_unique():
    assert len({create_refresh_token(1) for _ in range(20)}) == 20


@pytest.mark.parametrize(("token_factory", "expected_type"), [
    (create_access_token, JWTTokenTypes.REFRESH),
    (create_refresh_token, JWTTokenTypes.ACCESS),
])
def test_wrong_token_type_rejected(token_factory, expected_type):
    with pytest.raises(InvalidJWTToken, match="Invalid token type"):
        decode_jwt_token(token_factory(1), expected_type)


def test_expired_token_rejected():
    token = generate_jwt_token(1, JWTTokenTypes.ACCESS, timedelta(seconds=-1))

    with pytest.raises(ExpiredJWTToken):
        decode_jwt_token(token, JWTTokenTypes.ACCESS)


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c"])
def test_garbage_token_rejected(token):
    with pytest.raises(InvalidJWTToken):
        decode_jwt_token(token, JWTTokenTypes.ACCESS)


def test_token_signed_with_other_secret_rejected():
    token = jwt.encode(
        {"user_id": "1", "type": "access", "exp": 9999999999},
        "not-the-real-secret",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidJWTToken):
        decode_jwt_token(token, JWTTokenTypes.ACCESS)


@pytest.mark.parametrize("missing", ["user_id", "type", "exp"])
def test_token_without_required_claim_rejected(missing):
    payload = {"user_id": "1", "type": "access", "exp": 9999999999}
    del payload[missing]
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(InvalidJWTToken):
        decode_jwt_token(token, JWTTokenTypes.ACCESS)
