from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "postgres_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
