import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import database.models  # noqa
from config.settings import settings
from database.base import Base
from database.session import get_db_session
from main import app


@pytest.fixture(scope="session")
async def engine():
    # Safety guard: never drop tables in anything that isn't a test DB.
    assert settings.POSTGRES_DB.endswith("_test"), (
        f"Refusing to run: database '{settings.POSTGRES_DB}' is not a test database"
    )
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Each test runs in a transaction that is rolled back afterwards."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await trans.rollback()


@pytest.fixture
async def client(db_session):
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
