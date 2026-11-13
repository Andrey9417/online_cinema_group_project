import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "postgres_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    SENDGRID_API_KEY: str
    EMAIL_FROM: str
    API_URL: str

    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio")
    S3_STORAGE_PORT: int = os.getenv("MINIO_PORT", 9000)
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "some_password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "cinema-storage")

    S3_PUBLIC_URL: str = "http://localhost:9000"  # browser -> storage

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"


settings = Settings()
