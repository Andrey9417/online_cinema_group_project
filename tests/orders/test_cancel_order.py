import pytest
from fastapi import status

from database.models import OrderStatusEnum, UserGroupEnum

URL = "/api/v1/orders"


async def test_cancel_pending_order(
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

    response = await authenticated_client.patch(
        f"{URL}/{order.id}/cancel"
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == order.id
    assert data["user_id"] == regular_user.id
    assert data["status"] == OrderStatusEnum.CANCELED.value
    assert len(data["items"]) == 1
    assert data["items"][0]["movie"]["id"] == movie.id
    assert float(data["items"][0]["price_at_order"]) == float(movie.price)


async def test_cancel_another_users_order(
    regular_user,
    make_user,
    make_order,
    authenticate_as,
):
    another_user = await make_user(email="another@example.com")

    order = await make_order(user=another_user)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.patch(
        f"{URL}/{order.id}/cancel"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found"}


async def test_cancel_nonexistent_order(
    regular_user,
    authenticate_as,
):
    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.patch(
        f"{URL}/999999/cancel"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found"}


@pytest.mark.parametrize(
    "order_status",
    [
        OrderStatusEnum.PAID,
        OrderStatusEnum.CANCELED,
    ],
)
async def test_cancel_order_with_invalid_status(
    order_status,
    regular_user,
    make_order,
    authenticate_as,
):
    order = await make_order(
        user=regular_user,
        status=order_status,
    )

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.patch(
        f"{URL}/{order.id}/cancel"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": "Only pending orders can be canceled."
    }


@pytest.mark.parametrize(
    "group",
    [
        UserGroupEnum.MODERATOR,
        UserGroupEnum.ADMIN,
    ],
)
async def test_moderator_and_admin_cannot_cancel_another_users_order(
    group,
    make_user,
    make_order,
    authenticate_as,
):
    staff_user = await make_user(
        email=f"{group.value}@example.com",
        group=group,
    )
    another_user = await make_user(email="owner@example.com")

    order = await make_order(user=another_user)

    authenticated_client = authenticate_as(staff_user)

    response = await authenticated_client.patch(
        f"{URL}/{order.id}/cancel"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Order not found"}
