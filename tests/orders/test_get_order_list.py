from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import status

from database.models import OrderStatusEnum, UserGroupEnum
from tests.orders.conftest import URL


async def test_get_orders_empty_list(
        regular_user,
        authenticate_as,
):
    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"orders": []}


async def test_get_orders(
        regular_user,
        make_order,
        authenticate_as,
):
    order1 = await make_order(user=regular_user)
    order2 = await make_order(
        user=regular_user,
        total_amount=Decimal("25.50"),
    )

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(URL)

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    orders = data["orders"]

    assert len(orders) == 2
    assert {order["id"] for order in orders} == {order1.id, order2.id}


async def test_get_orders_returns_only_current_users_orders(
        regular_user,
        make_user,
        make_order,
        authenticate_as,
):
    other_user = await make_user(email="other@example.com")

    own_order = await make_order(user=regular_user)
    await make_order(user=other_user)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(URL)

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    orders = data["orders"]

    assert len(orders) == 1
    assert orders[0]["id"] == own_order.id
    assert orders[0]["user_id"] == regular_user.id


async def test_get_orders_pagination(
        regular_user,
        make_order,
        authenticate_as,
):
    order1 = await make_order(user=regular_user)
    order2 = await make_order(user=regular_user)
    order3 = await make_order(user=regular_user)

    authenticated_client = authenticate_as(regular_user)

    first_page_response = await authenticated_client.get(
        URL,
        params={"per_page": 2, "page": 1},
    )

    second_page_response = await authenticated_client.get(
        URL,
        params={"per_page": 2, "page": 2},
    )

    assert first_page_response.status_code == status.HTTP_200_OK
    assert second_page_response.status_code == status.HTTP_200_OK

    first_page = first_page_response.json()["orders"]
    second_page = second_page_response.json()["orders"]

    assert len(first_page) == 2
    assert len(second_page) == 1

    first_page_ids = {order["id"] for order in first_page}
    second_page_ids = {order["id"] for order in second_page}

    assert first_page_ids.isdisjoint(second_page_ids)

    assert first_page_ids | second_page_ids == {
        order1.id,
        order2.id,
        order3.id,
    }


async def test_regular_user_cannot_filter_orders_by_another_user(
        regular_user,
        make_user,
        make_order,
        authenticate_as,
):
    other_user = await make_user(email="other@example.com")

    own_order = await make_order(user=regular_user)
    await make_order(user=other_user)

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        URL,
        params={"user_id": other_user.id},
    )

    assert response.status_code == status.HTTP_200_OK

    orders = response.json()["orders"]

    assert len(orders) == 1
    assert orders[0]["id"] == own_order.id
    assert orders[0]["user_id"] == regular_user.id


@pytest.mark.parametrize(
    "requested_status",
    [
        OrderStatusEnum.PENDING,
        OrderStatusEnum.PAID,
        OrderStatusEnum.CANCELED,
    ],
)
async def test_get_orders_filters_by_status(
        requested_status,
        regular_user,
        make_order,
        authenticate_as,
):
    pending_order = await make_order(
        user=regular_user,
        status=OrderStatusEnum.PENDING,
    )
    paid_order = await make_order(
        user=regular_user,
        status=OrderStatusEnum.PAID,
    )
    cancelled_order = await make_order(
        user=regular_user,
        status=OrderStatusEnum.CANCELED,
    )

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        URL,
        params={"order_status": requested_status},
    )

    assert response.status_code == status.HTTP_200_OK

    orders = response.json()["orders"]

    expected_orders = {
        OrderStatusEnum.PENDING: pending_order,
        OrderStatusEnum.PAID: paid_order,
        OrderStatusEnum.CANCELED: cancelled_order,
    }

    expected_order = expected_orders[requested_status]

    assert len(orders) == 1
    assert orders[0]["id"] == expected_order.id
    assert orders[0]["status"] == requested_status.value


async def test_get_orders_invalid_date_range(
        regular_user,
        authenticate_as,
):
    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        URL,
        params={
            "start_date": "2026-11-20T00:00:00",
            "end_date": "2026-11-10T00:00:00",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Invalid date range"}


@pytest.mark.parametrize(
    ("date_filter", "filter_date", "expected_order"),
    [
        ("start_date", "2026-11-12T00:00:00", "newer"),
        ("end_date", "2026-11-12T23:59:59", "older"),
    ],
)
async def test_get_orders_filters_by_date(
        date_filter,
        filter_date,
        expected_order,
        db_session,
        regular_user,
        make_order,
        authenticate_as,
):
    older_order = await make_order(user=regular_user)
    newer_order = await make_order(user=regular_user)

    older_order.created_at = datetime(2026, 11, 10, 12, 0, 0)
    newer_order.created_at = datetime(2026, 11, 15, 12, 0, 0)

    await db_session.flush()

    authenticated_client = authenticate_as(regular_user)

    response = await authenticated_client.get(
        URL,
        params={date_filter: filter_date},
    )

    assert response.status_code == status.HTTP_200_OK

    orders = response.json()["orders"]

    expected = older_order if expected_order == "older" else newer_order

    assert len(orders) == 1
    assert orders[0]["id"] == expected.id


@pytest.mark.parametrize(
    "group",
    [
        UserGroupEnum.MODERATOR,
        UserGroupEnum.ADMIN,
    ],
)
async def test_moderator_and_admin_can_view_and_filter_all_users_orders(
        group,
        make_user,
        make_order,
        authenticate_as,
):
    user1 = await make_user(email="user1@example.com")
    user2 = await make_user(email="user2@example.com")
    privileged_user = await make_user(
        email="privileged@example.com",
        group=group,
    )

    order1 = await make_order(user=user1)
    order2 = await make_order(user=user2)

    authenticated_client = authenticate_as(privileged_user)

    response = await authenticated_client.get(URL)
    filtered_response = await authenticated_client.get(
        URL,
        params={"user_id": user1.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert filtered_response.status_code == status.HTTP_200_OK

    orders = response.json()["orders"]
    filtered_orders = filtered_response.json()["orders"]

    assert len(orders) == 2
    assert {order["id"] for order in orders} == {
        order1.id,
        order2.id,
    }

    assert len(filtered_orders) == 1
    assert filtered_orders[0]["id"] == order1.id
    assert filtered_orders[0]["user_id"] == user1.id
