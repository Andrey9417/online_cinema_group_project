import re

from pydantic import BaseModel, EmailStr, field_validator


class UserEmailSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, user_email: EmailStr):
        return user_email.lower()


class UserRegistrationRequestSchema(UserEmailSchema):
    raw_password: str

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


class UserResendActivationSchema(UserEmailSchema):
    pass


class MessageResponseSchema(BaseModel):
    message: str


class UserLoginRequestSchema(UserEmailSchema):
    raw_password: str


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserTokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class UserTokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogoutRequestSchema(UserTokenRefreshRequestSchema):
    pass
