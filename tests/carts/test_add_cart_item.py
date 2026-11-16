from unittest.mock import AsyncMock

import pytest

URL = "/carts/items"


@pytest.mark.asyncio
async def test_add_movie_creates_cart_and_item(
    auth_client, user, movie, cart_ids_of, cart_movie_ids
):
    response = await auth_client.post(URL, json={"movie_id": movie.id})

    assert response.status_code == 201
    assert len(response.json()["items"]) == 1
    cart_ids = await cart_ids_of(user.id)
    assert len(cart_ids) == 1
    assert await cart_movie_ids(cart_ids[0]) == {movie.id}


@pytest.mark.asyncio
async def test_add_movie_to_existing_cart(
    auth_client, user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies[:1])

    response = await auth_client.post(URL, json={"movie_id": movies[1].id})

    assert response.status_code == 201
    assert len(response.json()["items"]) == 2
    assert await cart_movie_ids(cart.id) == {movies[0].id, movies[1].id}


@pytest.mark.asyncio
async def test_add_several_movies_sequentially(auth_client, movies):
    first = await auth_client.post(URL, json={"movie_id": movies[0].id})
    second = await auth_client.post(URL, json={"movie_id": movies[1].id})

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(first.json()["items"]) == 1
    assert len(second.json()["items"]) == 2


@pytest.mark.asyncio
async def test_add_same_movie_twice_returns_409(
    auth_client, user, movie, make_cart, cart_movie_ids
):
    cart = await make_cart(user, [movie])

    response = await auth_client.post(URL, json={"movie_id": movie.id})

    assert response.status_code == 409
    assert await cart_movie_ids(cart.id) == {movie.id}


@pytest.mark.asyncio
async def test_add_unknown_movie_returns_404(auth_client):
    response = await auth_client.post(URL, json={"movie_id": 999999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."


@pytest.mark.asyncio
async def test_add_purchased_movie_returns_400_and_sends_email(
    auth_client, user, movie, monkeypatch, email_task, cart_ids_of
):
    monkeypatch.setattr(
        "services.carts.has_user_purchased_movie",
        AsyncMock(return_value=True),
    )

    response = await auth_client.post(URL, json={"movie_id": movie.id})

    assert response.status_code == 400
    assert response.json()["detail"] == "Movie has already been purchased."
    email_task.delay.assert_called_once_with(user.email, movie.name)
    assert await cart_ids_of(user.id) == []


@pytest.mark.asyncio
async def test_add_movie_does_not_send_email_for_new_movie(
    auth_client, movie, email_task
):
    response = await auth_client.post(URL, json={"movie_id": movie.id})

    assert response.status_code == 201
    email_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_two_users_can_add_same_movie(
    login_as, user, other_user, movie, cart_ids_of, cart_movie_ids
):
    first = await login_as(user).post(URL, json={"movie_id": movie.id})
    second = await login_as(other_user).post(URL, json={"movie_id": movie.id})

    assert first.status_code == 201
    assert second.status_code == 201
    user_cart = (await cart_ids_of(user.id))[0]
    other_cart = (await cart_ids_of(other_user.id))[0]
    assert user_cart != other_cart
    assert await cart_movie_ids(user_cart) == {movie.id}
    assert await cart_movie_ids(other_cart) == {movie.id}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{}, {"movie_id": "abc"}, {"movie_id": None}, {"id": 1}],
)
async def test_add_movie_rejects_invalid_payload(auth_client, payload):
    response = await auth_client.post(URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_movie_requires_authentication(client, movie):
    response = await client.post(URL, json={"movie_id": movie.id})

    assert response.status_code in (401, 403)
