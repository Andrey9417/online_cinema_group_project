import itertools
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from config.dependencies import get_current_user
from database.models.accounts import User, UserGroup, UserGroupEnum
from database.models.carts import Cart, CartItem
from database.models.movies import Certification, Movie
from main import app


@pytest.fixture(autouse=True)
def email_task(monkeypatch):
    task = MagicMock()
    monkeypatch.setattr(
        "services.carts.send_movie_already_purchased_email_task", task
    )
    return task


@pytest.fixture
async def groups(db_session):
    created = {}
    for name in UserGroupEnum:
        group = UserGroup(name=name)
        db_session.add(group)
        created[name] = group
    await db_session.commit()
    return {name: group.id for name, group in created.items()}


@pytest.fixture
def make_user(db_session, groups):
    counter = itertools.count(1)

    async def factory(group=UserGroupEnum.USER):
        index = next(counter)
        user = User(
            email=f"user{index}@example.com",
            hashed_password="hashed",
            is_active=True,
            group_id=groups[group],
        )
        db_session.add(user)
        await db_session.commit()
        return SimpleNamespace(id=user.id, email=user.email, group=group)

    return factory


@pytest.fixture
async def user(make_user):
    return await make_user(UserGroupEnum.USER)


@pytest.fixture
async def other_user(make_user):
    return await make_user(UserGroupEnum.USER)


@pytest.fixture
async def moderator(make_user):
    return await make_user(UserGroupEnum.MODERATOR)


@pytest.fixture
async def admin(make_user):
    return await make_user(UserGroupEnum.ADMIN)


@pytest.fixture
async def certification(db_session):
    entity = Certification(name="PG-13")
    db_session.add(entity)
    await db_session.commit()
    return entity.id


@pytest.fixture
def make_movie(db_session, certification):
    counter = itertools.count(1)

    async def factory():
        index = next(counter)
        movie = Movie(
            name=f"Movie {index}",
            year=2000 + index,
            time=100 + index,
            imdb=7.5,
            votes=1000,
            description="Description",
            price=Decimal("9.99"),
            certification_id=certification,
        )
        db_session.add(movie)
        await db_session.commit()
        return SimpleNamespace(id=movie.id, name=movie.name)

    return factory


@pytest.fixture
async def movie(make_movie):
    return await make_movie()


@pytest.fixture
async def movies(make_movie):
    return [await make_movie() for _ in range(3)]


@pytest.fixture
def make_cart(db_session):
    async def factory(owner, items=()):
        cart = Cart(user_id=owner.id)
        db_session.add(cart)
        await db_session.flush()
        for item in items:
            db_session.add(CartItem(cart_id=cart.id, movie_id=item.id))
        await db_session.commit()
        return SimpleNamespace(id=cart.id)

    return factory


@pytest.fixture
def cart_movie_ids(db_session):
    async def fetch(cart_id):
        result = await db_session.execute(
            select(CartItem.movie_id).where(CartItem.cart_id == cart_id)
        )
        return set(result.scalars().all())

    return fetch


@pytest.fixture
def cart_ids_of(db_session):
    async def fetch(user_id):
        result = await db_session.execute(
            select(Cart.id).where(Cart.user_id == user_id)
        )
        return list(result.scalars().all())

    return fetch


@pytest.fixture
def authenticate():
    def apply(account):
        principal = SimpleNamespace(
            id=account.id,
            email=account.email,
            group=SimpleNamespace(name=account.group),
        )
        app.dependency_overrides[get_current_user] = lambda: principal

    yield apply
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def login_as(client, authenticate):
    def apply(account):
        authenticate(account)
        return client

    return apply


@pytest.fixture
def auth_client(client, user, authenticate):
    authenticate(user)
    return client
