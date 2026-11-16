import pytest

URL = "/carts/users"


@pytest.mark.asyncio
async def test_moderator_can_view_user_cart(
    login_as, moderator, user, movies, make_cart
):
    await make_cart(user, movies[:2])

    response = await login_as(moderator).get(f"{URL}/{user.id}")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


@pytest.mark.asyncio
async def test_admin_can_view_user_cart(
    login_as, admin, user, movies, make_cart
):
    await make_cart(user, movies)

    response = await login_as(admin).get(f"{URL}/{user.id}")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


@pytest.mark.asyncio
async def test_regular_user_cannot_view_other_user_cart(
    login_as, user, other_user, movies, make_cart
):
    await make_cart(other_user, movies)

    response = await login_as(user).get(f"{URL}/{other_user.id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_regular_user_cannot_view_own_cart_via_staff_endpoint(
    login_as, user, make_cart
):
    await make_cart(user)

    response = await login_as(user).get(f"{URL}/{user.id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_staff_gets_404_when_user_has_no_cart(
    login_as, moderator, user
):
    response = await login_as(moderator).get(f"{URL}/{user.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found."


@pytest.mark.asyncio
async def test_staff_gets_404_for_unknown_user(login_as, moderator):
    response = await login_as(moderator).get(f"{URL}/999999")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", ["0", "-1", "abc"])
async def test_staff_get_cart_rejects_invalid_user_id(
    login_as, moderator, user_id
):
    response = await login_as(moderator).get(f"{URL}/{user_id}")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_staff_get_cart_requires_authentication(client, user):
    response = await client.get(f"{URL}/{user.id}")

    assert response.status_code in (401, 403)
