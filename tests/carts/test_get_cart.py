import pytest

URL = "/api/v1/carts/"


@pytest.mark.asyncio
async def test_get_cart_creates_cart_when_missing(
    auth_client, user, cart_ids_of
):
    assert await cart_ids_of(user.id) == []

    response = await auth_client.get(URL)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert len(await cart_ids_of(user.id)) == 1


@pytest.mark.asyncio
async def test_get_cart_returns_existing_cart_with_items(
    auth_client, user, movies, make_cart
):
    await make_cart(user, movies[:2])

    response = await auth_client.get(URL)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


@pytest.mark.asyncio
async def test_get_cart_is_idempotent(auth_client, user, cart_ids_of):
    first = await auth_client.get(URL)
    second = await auth_client.get(URL)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(await cart_ids_of(user.id)) == 1


@pytest.mark.asyncio
async def test_get_cart_does_not_return_other_users_items(
    auth_client, user, other_user, movies, make_cart
):
    await make_cart(other_user, movies)
    await make_cart(user, movies[:1])

    response = await auth_client.get(URL)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_cart_requires_authentication(client):
    response = await client.get(URL)

    assert response.status_code in (401, 403)

