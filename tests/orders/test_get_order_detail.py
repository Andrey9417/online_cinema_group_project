import pytest
from fastapi import status

from database.models import OrderStatusEnum, UserGroupEnum
from tests.orders.conftest import URL


async def test_get_order_detail(
        regular_user,
        make_movie,
        make_order_with_movie,
        authenticate_as,
):
    movie = await make_movie()

    order = await make_order_with_movie(
        user=regular_user,
        movie=movie,
        order_status=OrderStatusEnum.PENDING,
    )

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        f"{URL}/{order.id}"
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == order.id
    assert data["user_id"] == regular_user.id
    assert data["status"] == OrderStatusEnum.PENDING.value

    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["movie"]["id"] == movie.id
    assert item["price_at_order"] == str(movie.price)


async def test_regular_user_cannot_retrieve_another_users_order(
        regular_user,
        make_user,
        make_order,
        authenticate_as,
):
    other_user = await make_user(email="other@example.com")

    other_order = await make_order(user=other_user)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        f"{URL}/{other_order.id}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found"}


async def test_get_nonexistent_order(
        regular_user,
        authenticate_as,
):
    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        f"{URL}/999999"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found"}


@pytest.mark.parametrize(
    "group",
    [
        UserGroupEnum.MODERATOR,
        UserGroupEnum.ADMIN,
    ],
)
async def test_moderator_and_admin_can_retrieve_another_users_order(
        group,
        make_user,
        make_order,
        authenticate_as,
):
    other_user = await make_user(email="other@example.com")

    privileged_user = await make_user(
        email="privileged@example.com",
        group=group,
    )

    other_order = await make_order(user=other_user)

    authenticated_client = authenticate_as(privileged_user)

    response = await authenticated_client.get(
        f"{URL}/{other_order.id}"
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == other_order.id
    assert data["user_id"] == other_user.id
