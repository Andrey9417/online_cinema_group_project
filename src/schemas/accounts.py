import re
from datetime import date
from io import BytesIO

from PIL import Image
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict

from database.models import GenderEnum, UserGroupEnum


def val_password(raw_password: str):
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
        return val_password(raw_password)


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
            name_field = name_field.strip()
        return name_field

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, user_date: date | None):
        if user_date:
            if user_date > date.today():
                raise ValueError("You can not register today while being born in the future")
            if user_date.year < 1900:
                raise ValueError("Invalid birth date - year must be greater than 1900.")
        return user_date

    @field_validator("info")
    @classmethod
    def validate_info(cls, info_field: str | None):
        if info_field:
            info_field = info_field.strip()
        return info_field


class UserProfileAvatarSchema(BaseModel):
    avatar: UploadFile

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, avatar: UploadFile):
        supported_image_formats = ["JPEG", "PNG"]
        max_file_size = 2 * 1024 * 1024
        if avatar.size and avatar.size > max_file_size:
            raise ValueError("Image size exceeds 2 MB")
        contents = avatar.file.read()
        try:
            image = Image.open(BytesIO(contents))
            image.verify()
        except (IOError, Image.DecompressionBombError) as e:
            raise ValueError("Invalid image format") from e
        if image.format not in supported_image_formats:
            raise ValueError(
                f"Unsupported image format: {image.format}. "
                f"Use one of next: {supported_image_formats}"
            )
        avatar.file.seek(0)
        return avatar


class UserProfileResponseSchema(BaseModel):
    first_name: str | None
    last_name: str | None
    gender: GenderEnum | None
    date_of_birth: date | None
    info: str | None
    avatar: str | None

    model_config = ConfigDict(from_attributes=True)


class PasswordChangeRequestSchema(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, new_password: str):
        return val_password(new_password)


class PasswordResetRequestSchema(UserEmailSchema):
    pass


class PasswordResetCompleteSchema(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, new_password: str):
        return val_password(new_password)


class UserGroupChangeRequestSchema(BaseModel):
    group: UserGroupEnum


class AdminUserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    group: UserGroupEnum
