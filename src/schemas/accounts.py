import re
from datetime import date

from fastapi import UploadFile
from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict

from database.models import GenderEnum


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


class UserProfileUpdateSchema(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = Field(default=None, max_length=1000)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, name_field: str | None):
        if name_field:
            if re.search(r'^[A-Za-z]*$', name_field) is None:
                raise ValueError(f'{name_field} contains non-english letters')
            name_field.lower()
        return name_field

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, user_date: date | None):
        if user_date:
            if user_date > date.today():
                raise ValueError("You can not register today while being born in the future")
            if user_date.year < 1900:
                raise ValueError('Invalid birth date - year must be greater than 1900.')
            age = (date.today() - user_date).days // 365
            if age < 18:
                raise ValueError('You must be at least 18 years old to register.')
        return user_date

    @field_validator("info")
    @classmethod
    def validate_info(cls, info_field: str | None):
        if info_field:
            info_field.strip()
        return info_field


class UserProfileResponseSchema(BaseModel):
    first_name: str | None
    last_name: str | None
    gender: GenderEnum | None
    date_of_birth: date | None
    info: str | None
    avatar: UploadFile | None

    model_config = ConfigDict(from_attributes=True)
