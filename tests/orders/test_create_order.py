from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from database.models import CartItem, Order, OrderItem, OrderStatusEnum
from tests.orders.conftest import URL


async def test_create_order_success(
        db_session,
        regular_user,
        make_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
):
    movie = await make_movie()

    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=movie)

    authenticated_client = authenticate_as(regular_user)
    response = await authenticated_client.post(f"{URL}")

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    order = data["order"]

    assert order["user_id"] == regular_user.id
    assert order["status"] == "pending"
    assert order["total_amount"] == str(movie.price)

    assert len(order["items"]) == 1
    assert order["items"][0]["movie_id"] == movie.id
    assert order["items"][0]["price_at_order"] == str(movie.price)

    assert data["excluded_movies"] == []

    result = await db_session.scalars(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )

    assert result.all() == []


async def test_create_order_without_a_cart(
        regular_user,
        authenticate_as,
):
    authenticated_client = authenticate_as(regular_user)
    response = await authenticated_client.post(f"{URL}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Cart not found"}


async def test_create_order_empty_cart(
        regular_user,
        make_cart,
        authenticate_as,
):
    await make_cart(user=regular_user)
    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.post(f"{URL}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Cart is empty"}


async def test_create_order_with_multiple_movies(
        db_session,
        regular_user,
        make_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
):
    movie1 = await make_movie()
    movie2 = await make_movie(price=Decimal("17.00"), name="Movie title2")
    movie3 = await make_movie(price=Decimal("15.45"), name="Movie title3")

    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=movie1)
    await make_cart_item(cart=cart, movie=movie2)
    await make_cart_item(cart=cart, movie=movie3)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.post(f"{URL}")
    data = response.json()
    order = data["order"]

    assert response.status_code == status.HTTP_201_CREATED
    assert order["user_id"] == regular_user.id
    assert order["status"] == "pending"
    assert order["total_amount"] == str(movie1.price + movie2.price + movie3.price)
    assert len(order["items"]) == 3

    assert order["items"][0]["movie_id"] == movie1.id
    assert order["items"][0]["price_at_order"] == str(movie1.price)

    assert order["items"][1]["movie_id"] == movie2.id
    assert order["items"][1]["price_at_order"] == str(movie2.price)

    assert order["items"][2]["movie_id"] == movie3.id
    assert order["items"][2]["price_at_order"] == str(movie3.price)

    assert data["excluded_movies"] == []

    result = await db_session.scalars(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )

    assert result.all() == []


async def test_order_preserves_movie_price(
        db_session,
        regular_user,
        make_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
):
    movie = await make_movie()

    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=movie)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.post(f"{URL}")
    data = response.json()
    order = data["order"]

    movie.price = Decimal("20.00")
    await db_session.flush()

    order_from_db = await db_session.get(Order, order["id"])
    order_item = await db_session.scalar(
        select(OrderItem)
        .where(OrderItem.order_id == order["id"])
    )

    assert order_from_db.total_amount == Decimal("12.99")
    assert movie.price == Decimal("20.00")
    assert order_item.price_at_order == Decimal("12.99")


@pytest.mark.parametrize(
    ("movie_name", "order_status"),
    [
        ("Purchased Movie", OrderStatusEnum.PAID),
        ("Pending Movie", OrderStatusEnum.PENDING),
    ],
)
async def test_create_order_excludes_unavailable_movie(
        movie_name,
        order_status,
        regular_user,
        make_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
        make_order_with_movie,
        db_session
):
    unavailable_movie = await make_movie(name=movie_name)
    available_movie = await make_movie(name="Available Movie")

    await make_order_with_movie(
        user=regular_user,
        movie=unavailable_movie,
        order_status=order_status,
    )

    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=unavailable_movie)
    await make_cart_item(cart=cart, movie=available_movie)

    authenticated_client = authenticate_as(regular_user)
    response = await authenticated_client.post(URL)

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    order = data["order"]

    assert len(order["items"]) == 1
    assert order["items"][0]["movie_id"] == available_movie.id
    assert order["total_amount"] == str(available_movie.price)
    assert len(data["excluded_movies"]) == 1

    result = await db_session.scalars(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )

    remaining_items = result.all()

    assert len(remaining_items) == 1
    assert remaining_items[0].movie_id == unavailable_movie.id


async def test_create_order_when_all_movies_are_unavailable(
        regular_user,
        make_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
        make_order_with_movie,
        db_session
):
    movie = await make_movie()

    await make_order_with_movie(
        user=regular_user,
        movie=movie,
        order_status=OrderStatusEnum.PAID,
    )

    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=movie)

    authenticated_client = authenticate_as(regular_user)
    response = await authenticated_client.post(URL)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "No available movies"}

    result = await db_session.scalars(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    remaining_items = result.all()

    assert len(remaining_items) == 1
    assert remaining_items[0].movie_id == movie.id


@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatusEnum.PAID,
        OrderStatusEnum.PENDING,
    ],
)
async def test_create_order_ignores_another_users_orders(
        order_status,
        regular_user,
        make_user,
        make_movie,
        make_order_with_movie,
        make_cart,
        make_cart_item,
        authenticate_as,
):
    other_user = await make_user(email="other@example.com")
    movie = await make_movie(name="Shared Movie")

    # Another user already has this movie in an order.
    await make_order_with_movie(
        user=other_user,
        movie=movie,
        order_status=order_status,
    )

    # The current user adds the same movie to their cart.
    cart = await make_cart(user=regular_user)
    await make_cart_item(cart=cart, movie=movie)

    authenticated_client = authenticate_as(regular_user)
    response = await authenticated_client.post(URL)

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    order = data["order"]

    assert len(order["items"]) == 1
    assert order["items"][0]["movie_id"] == movie.id
    assert order["total_amount"] == str(movie.price)
    assert data["excluded_movies"] == []
