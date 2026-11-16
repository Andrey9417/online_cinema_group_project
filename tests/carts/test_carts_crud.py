import pytest

from crud.carts import (
    add_movie_to_cart,
    clear_cart,
    create_cart,
    delete_cart,
    get_cart_by_user,
    get_cart_item,
    has_user_purchased_movie,
    is_movie_in_any_cart,
    remove_movie_from_cart,
)
from exceptions.carts import EntityAlreadyExists, EntityNotFound


@pytest.mark.asyncio
async def test_get_cart_by_user_returns_none_when_missing(db_session, user):
    assert await get_cart_by_user(db_session, user.id) is None


@pytest.mark.asyncio
async def test_get_cart_by_user_loads_items(
    db_session, user, movies, make_cart
):
    cart = await make_cart(user, movies[:2])

    result = await get_cart_by_user(db_session, user.id)

    assert result.id == cart.id
    assert {item.movie_id for item in result.items} == {
        movies[0].id,
        movies[1].id,
    }
    assert all(item.movie.id == item.movie_id for item in result.items)


@pytest.mark.asyncio
async def test_create_cart(db_session, user):
    cart = await create_cart(db_session, user.id)

    assert cart.user_id == user.id
    assert cart.items == []


@pytest.mark.asyncio
async def test_create_cart_duplicate_raises_already_exists(db_session, user):
    await create_cart(db_session, user.id)

    with pytest.raises(EntityAlreadyExists):
        await create_cart(db_session, user.id)


@pytest.mark.asyncio
async def test_create_cart_for_unknown_user_raises_not_found(db_session):
    with pytest.raises(EntityNotFound):
        await create_cart(db_session, 999999)


@pytest.mark.asyncio
async def test_add_movie_to_cart_returns_item_with_movie(
    db_session, user, movie, make_cart
):
    cart = await make_cart(user)

    item = await add_movie_to_cart(db_session, cart.id, movie.id)

    assert item.cart_id == cart.id
    assert item.movie_id == movie.id
    assert item.movie.name == movie.name
    assert item.added_at is not None


@pytest.mark.asyncio
async def test_add_movie_to_cart_duplicate_raises_already_exists(
    db_session, user, movie, make_cart
):
    cart = await make_cart(user, [movie])

    with pytest.raises(EntityAlreadyExists):
        await add_movie_to_cart(db_session, cart.id, movie.id)


@pytest.mark.asyncio
async def test_add_unknown_movie_to_cart_raises_not_found(
    db_session, user, make_cart
):
    cart = await make_cart(user)

    with pytest.raises(EntityNotFound):
        await add_movie_to_cart(db_session, cart.id, 999999)


@pytest.mark.asyncio
async def test_get_cart_item(db_session, user, movies, make_cart):
    cart = await make_cart(user, movies[:1])

    found = await get_cart_item(db_session, cart.id, movies[0].id)
    missing = await get_cart_item(db_session, cart.id, movies[1].id)

    assert found is not None
    assert found.movie.id == movies[0].id
    assert missing is None


@pytest.mark.asyncio
async def test_remove_movie_from_cart_returns_true_when_removed(
    db_session, user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies[:2])

    removed = await remove_movie_from_cart(db_session, cart.id, movies[0].id)

    assert removed is True
    assert await cart_movie_ids(cart.id) == {movies[1].id}


@pytest.mark.asyncio
async def test_remove_movie_from_cart_returns_false_when_absent(
    db_session, user, movies, make_cart
):
    cart = await make_cart(user, movies[:1])

    removed = await remove_movie_from_cart(db_session, cart.id, movies[1].id)

    assert removed is False


@pytest.mark.asyncio
async def test_clear_cart_removes_only_target_cart_items(
    db_session, user, other_user, movies, make_cart, cart_movie_ids
):
    cart = await make_cart(user, movies)
    other_cart = await make_cart(other_user, movies[:1])

    await clear_cart(db_session, cart.id)

    assert await cart_movie_ids(cart.id) == set()
    assert await cart_movie_ids(other_cart.id) == {movies[0].id}


@pytest.mark.asyncio
async def test_delete_cart_removes_cart_and_items(
    db_session, user, movies, make_cart, cart_movie_ids, cart_ids_of
):
    cart = await make_cart(user, movies)
    loaded = await get_cart_by_user(db_session, user.id)

    await delete_cart(db_session, loaded)

    assert await cart_ids_of(user.id) == []
    assert await cart_movie_ids(cart.id) == set()


@pytest.mark.asyncio
async def test_is_movie_in_any_cart(db_session, user, movies, make_cart):
    await make_cart(user, movies[:1])

    assert await is_movie_in_any_cart(db_session, movies[0].id) is True
    assert await is_movie_in_any_cart(db_session, movies[1].id) is False


@pytest.mark.asyncio
async def test_has_user_purchased_movie_false_without_orders(
    db_session, user, movie
):
    assert await has_user_purchased_movie(db_session, user.id, movie.id) is False
