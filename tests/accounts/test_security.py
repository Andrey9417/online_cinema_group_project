import pytest

from database.models import User
from security.passwords import hash_password, verify_password
from security.tokens import generate_regular_token


def test_hash_password_is_not_plain_text_and_verifies():
    hashed = hash_password("Str0ng!Pass")

    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed)
    assert not verify_password("Wr0ng!Pass", hashed)


def test_hash_password_is_salted():
    assert hash_password("Str0ng!Pass") != hash_password("Str0ng!Pass")


def test_generate_token_is_unique_and_url_safe():
    tokens = {generate_regular_token() for _ in range(100)}

    assert len(tokens) == 100
    for token in tokens:
        assert len(token) == 43  # 32 random bytes, base64url without padding
        assert all(c.isalnum() or c in "-_" for c in token)


def test_generate_token_custom_length():
    assert len(generate_regular_token(16)) == 22


def test_user_cool_create_hashes_password():
    user = User.cool_create(email="user@example.com", raw_password="Str0ng!Pass", group_id=1)

    assert user.email == "user@example.com"
    assert user.group_id == 1
    assert verify_password("Str0ng!Pass", user.hashed_password)


def test_user_password_attribute_is_not_readable():
    user = User.cool_create(email="user@example.com", raw_password="Str0ng!Pass", group_id=1)

    with pytest.raises(AttributeError):
        _ = user.password
