import pytest
from httpx import AsyncClient

from config.dependencies import get_current_user
from database.models import User, UserGroup, UserGroupEnum
from main import app

API = "/api/v1"


@pytest.fixture(autouse=True)
async def user_groups(db_session):
    """create_all builds empty tables — seed groups like the migration does."""
    groups = {name: UserGroup(name=name) for name in UserGroupEnum}
    db_session.add_all(groups.values())
    await db_session.commit()
    return groups


@pytest.fixture
async def make_user(db_session, user_groups):
    async def _make_user(
            email: str = "user@example.com",
            group: UserGroupEnum = UserGroupEnum.USER,
    ) -> User:
        user = User.cool_create(
            email=email,
            raw_password="Str0ng!Pass",
            group_id=user_groups[group].id,
        )
        user.is_active = True
        user.group = user_groups[group]  # in-memory → no async lazy-load
        db_session.add(user)
        await db_session.commit()
        return user

    return _make_user


@pytest.fixture
async def regular_user(make_user):
    return await make_user(email="user@example.com", group=UserGroupEnum.USER)


@pytest.fixture
async def moderator(make_user):
    return await make_user(
        email="moderator@example.com", group=UserGroupEnum.MODERATOR
    )


@pytest.fixture
def as_user(client):
    """Return the test client acting as `user` (overrides auth dependency)."""
    def _as_user(user: User) -> AsyncClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    return _as_user


@pytest.fixture
async def catalog(as_user, moderator):
    """Seed reference data via the API; return created ids."""
    client = as_user(moderator)
    cert = await client.post(f"{API}/certifications/", json={"name": "PG-13"})
    action = await client.post(f"{API}/genres/", json={"name": "Action"})
    drama = await client.post(f"{API}/genres/", json={"name": "Drama"})
    star = await client.post(f"{API}/stars/", json={"name": "Keanu Reeves"})
    director = await client.post(
        f"{API}/directors/", json={"name": "Chad Stahelski"}
    )
    for resp in (cert, action, drama, star, director):
        assert resp.status_code == 201, resp.text
    return {
        "cert_id": cert.json()["id"],
        "action_id": action.json()["id"],
        "drama_id": drama.json()["id"],
        "star_id": star.json()["id"],
        "director_id": director.json()["id"],
    }


@pytest.fixture
def movie_payload(catalog):
    return {
        "name": "The Matrix",
        "year": 1999,
        "time": 136,
        "imdb": 8.7,
        "votes": 1000,
        "description": "A hacker learns the truth about his reality.",
        "price": "9.99",
        "certification_id": catalog["cert_id"],
        "genre_ids": [catalog["action_id"]],
        "star_ids": [catalog["star_id"]],
        "director_ids": [catalog["director_id"]],
    }


@pytest.fixture
def make_movie(as_user, moderator, movie_payload):
    async def _make_movie(**overrides) -> dict:
        payload = {**movie_payload, **overrides}
        resp = await as_user(moderator).post(f"{API}/movies/", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make_movie
