import pytest

URL = "/carts/items"


@pytest.mark.asyncio
async def test_clear_cart_removes_all_items(
    auth_client, user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies)

    response = await auth_client.delete(URL)

    assert response.status_code == 204
    assert response.content == b""
    assert await cart_movie_ids(cart.id) == set()


@pytest.mark.asyncio
async def test_clear_cart_keeps_cart_itself(
    auth_client, user, movies, make_cart, cart_ids_of
):
    cart = await make_cart(user, movies)

    await auth_client.delete(URL)

    assert await cart_ids_of(user.id) == [cart.id]


@pytest.mark.asyncio
async def test_clear_empty_cart_returns_204(auth_client, user, make_cart):
    await make_cart(user)

    response = await auth_client.delete(URL)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_clear_cart_without_cart_returns_404(auth_client):
    response = await auth_client.delete(URL)

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found."


@pytest.mark.asyncio
async def test_clear_cart_does_not_touch_other_users_cart(
    auth_client, user, other_user, movies, make_cart, cart_movie_ids
):
    await make_cart(user, movies[:2])
    other_cart = await make_cart(other_user, movies)

    response = await auth_client.delete(URL)

    assert response.status_code == 204
    assert await cart_movie_ids(other_cart.id) == {m.id for m in movies}


@pytest.mark.asyncio
async def test_clear_cart_requires_authentication(client):
    response = await client.delete(URL)

    assert response.status_code in (401, 403)
