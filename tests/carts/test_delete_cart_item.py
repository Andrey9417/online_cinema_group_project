import pytest

URL = "/api/v1/carts/items"


@pytest.mark.asyncio
async def test_delete_movie_from_cart(
    auth_client, user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies)

    response = await auth_client.delete(f"{URL}/{movies[0].id}")

    assert response.status_code == 204
    assert response.content == b""
    assert await cart_movie_ids(cart.id) == {movies[1].id, movies[2].id}


@pytest.mark.asyncio
async def test_delete_last_movie_keeps_empty_cart(
    auth_client, user, movie, make_cart, cart_movie_ids, cart_ids_of
):
    cart = await make_cart(user, [movie])

    response = await auth_client.delete(f"{URL}/{movie.id}")

    assert response.status_code == 204
    assert await cart_movie_ids(cart.id) == set()
    assert await cart_ids_of(user.id) == [cart.id]


@pytest.mark.asyncio
async def test_delete_movie_not_in_cart_returns_404(
    auth_client, user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies[:1])

    response = await auth_client.delete(f"{URL}/{movies[1].id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."
    assert await cart_movie_ids(cart.id) == {movies[0].id}


@pytest.mark.asyncio
async def test_delete_movie_without_cart_returns_404(auth_client, movie):
    response = await auth_client.delete(f"{URL}/{movie.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found."


@pytest.mark.asyncio
async def test_delete_movie_does_not_touch_other_users_cart(
    auth_client, user, other_user, movies, make_cart, cart_movie_ids
):
    await make_cart(user, movies[:1])
    other_cart = await make_cart(other_user, movies[:1])

    response = await auth_client.delete(f"{URL}/{movies[0].id}")

    assert response.status_code == 204
    assert await cart_movie_ids(other_cart.id) == {movies[0].id}


@pytest.mark.asyncio
async def test_delete_movie_cannot_remove_from_other_users_cart(
    auth_client, other_user, movies, make_cart, cart_movie_ids
):
    other_cart = await make_cart(other_user, movies[:1])

    response = await auth_client.delete(f"{URL}/{movies[0].id}")

    assert response.status_code == 404
    assert await cart_movie_ids(other_cart.id) == {movies[0].id}


@pytest.mark.asyncio
async def test_delete_movie_rejects_invalid_id(auth_client):
    response = await auth_client.delete(f"{URL}/abc")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_movie_requires_authentication(client, movie):
    response = await client.delete(f"{URL}/{movie.id}")

    assert response.status_code in (401, 403)
