import pytest
from pydantic import ValidationError

from schemas.accounts import UserRegistrationRequestSchema, UserResendActivationSchema


def make(password="Str0ng!Pass", email="user@example.com"):
    return UserRegistrationRequestSchema(email=email, raw_password=password)


@pytest.mark.parametrize("password", [
    "Aa1@aaaa",  # exactly 8 chars
    "Aa1@" + "a" * 124,  # exactly 128 chars
    "Aa1@$!%*?&#",  # every allowed special char
])
def test_valid_passwords(password):
    assert make(password=password).raw_password == password


@pytest.mark.parametrize(("password", "error"), [
    ("Aa1@aaa", "between 8 and 128"),
    ("Aa1@" + "a" * 125, "between 8 and 128"),
    ("aaaaaa1@", "uppercase"),
    ("AAAAAA1@", "lower"),
    ("Aaaaaaa@", "digit"),
    ("Aaaaaaa1", "special character"),
    ("Aaaaaaa1^", "special character"),  # ^ is not in the allowed set
])
def test_invalid_passwords(password, error):
    with pytest.raises(ValidationError, match=error):
        make(password=password)


def test_registration_email_is_lowercased():
    assert make(email="John.Doe@Example.COM").email == "john.doe@example.com"


@pytest.mark.parametrize("email", ["plainaddress", "@example.com", "user@", ""])
def test_registration_invalid_email(email):
    with pytest.raises(ValidationError):
        make(email=email)


def test_resend_schema_requires_valid_email():
    assert UserResendActivationSchema(email="user@example.com").email == "user@example.com"
    with pytest.raises(ValidationError):
        UserResendActivationSchema(email="nope")
