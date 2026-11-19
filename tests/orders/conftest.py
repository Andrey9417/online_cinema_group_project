from decimal import Decimal

import pytest

from config.dependencies import get_current_user
from database.models import Cart, CartItem, Movie, UserGroupEnum, UserGroup, User, ActivationToken, Certification, \
    OrderStatusEnum, OrderItem, Order
from main import app

TEST_PASSWORD = "!@PaSsWoRd354"
URL = "/api/v1/orders"


@pytest.fixture(autouse=True)
async def user_groups(db_session):
    groups = {name: UserGroup(name=name) for name in UserGroupEnum}
    db_session.add_all(groups.values())
    await db_session.commit()
    return groups


@pytest.fixture
def make_user(db_session, user_groups):
    async def _make_user(
        email="user@example.com",
        is_active=True,
        group=UserGroupEnum.USER,
    ):
        user = User.cool_create(
            email=email,
            raw_password=TEST_PASSWORD,
            group_id=user_groups[group].id,
        )
        user.is_active = is_active

        db_session.add(user)
        await db_session.flush()

        token = ActivationToken(user_id=user.id)
        db_session.add(token)

        await db_session.flush()
        return user

    return _make_user


@pytest.fixture
async def regular_user(make_user):
    return await make_user()


@pytest.fixture
def authenticate_as(client):
    def _authenticate_as(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    return _authenticate_as


@pytest.fixture
async def certification(db_session):
    certification = Certification(name="PG-13")
    db_session.add(certification)
    await db_session.flush()
    return certification


@pytest.fixture
def make_movie(db_session, certification):
    async def _make_movie(**overrides) -> Movie:
        movie_data = {
            "name": "Test Movie",
            "year": 2024,
            "time": 120,
            "imdb": 8.5,
            "votes": 1000,
            "meta_score": 85.0,
            "gross": 1000000.0,
            "description": "A test movie description.",
            "price": Decimal("12.99"),
            "certification_id": certification.id,
        }
        movie_data.update(overrides)

        movie = Movie(**movie_data)
        db_session.add(movie)
        await db_session.flush()

        return movie

    return _make_movie


@pytest.fixture
def make_cart(db_session):
    async def _make_cart(user) -> Cart:
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        return cart

    return _make_cart


@pytest.fixture
def make_cart_item(db_session):
    async def _make_cart_item(cart, movie) -> CartItem:
        cart_item = CartItem(
            cart_id=cart.id,
            movie_id=movie.id,
        )
        db_session.add(cart_item)
        await db_session.flush()
        return cart_item

    return _make_cart_item


@pytest.fixture
def make_order(db_session):
    async def _make_order(
        user,
        total_amount: Decimal = Decimal("12.99"),
        status: OrderStatusEnum = OrderStatusEnum.PENDING,
    ):
        order = Order(
            user_id=user.id,
            total_amount=total_amount,
            status=status,
        )
        db_session.add(order)
        await db_session.flush()

        return order

    return _make_order


@pytest.fixture
def make_order_with_movie(db_session, make_order):
    async def _make_order_with_movie(user, movie, order_status):
        order = await make_order(
            user=user,
            status=order_status,
        )

        db_session.add(
            OrderItem(
                order_id=order.id,
                movie_id=movie.id,
                price_at_order=movie.price,
            )
        )
        await db_session.flush()

        return order

    return _make_order_with_movie
