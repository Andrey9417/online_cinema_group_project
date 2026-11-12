import re

from pydantic import BaseModel, EmailStr, field_validator


class UserRegistrationRequestSchema(BaseModel):
    email: EmailStr
    raw_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, user_email: EmailStr):
        return user_email.lower()

    @field_validator("raw_password")
    @classmethod
    def validate_password(cls, raw_password: str):
        if not 8 <= len(raw_password) <= 128:
            raise ValueError("Password must be between 8 and 128 chars.")
        if not re.search(r'[A-Z]', raw_password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', raw_password):
            raise ValueError("Password must contain at least one lower letter.")
        if not re.search(r'\d', raw_password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r'[@$!%*?&#]', raw_password):
            raise ValueError("Password must contain at least one special character: @, $, !, %, *, ?, #, &.")
        return raw_password


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr


class MessageResponseSchema(BaseModel):
    message: str
