from sqlalchemy.ext.asyncio import AsyncSession

from crud.carts import (
    get_cart_by_user,
    create_cart,
    clear_cart,
    remove_movie_from_cart,
    add_movie_to_cart
)
from crud.movies import get_movie_by_id
from database.models import Cart
from exceptions.carts import EntityAlreadyExists, DBError, EntityNotFound


async def get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    cart = await get_cart_by_user(db=db, user_id=user_id)

    if cart is None:
        try:
            cart = await create_cart(db=db, user_id=user_id)
        except EntityAlreadyExists:
            cart = await get_cart_by_user(db=db, user_id=user_id)

    if cart is None:
        raise DBError("Failed to retrieve cart.")

    return cart


async def clear_user_cart(
        db: AsyncSession,
        user_id: int,
) -> None:
    cart = await get_cart_by_user(db=db, user_id=user_id)
    if cart is None:
        raise EntityNotFound("Cart not found.")
    await clear_cart(db=db, cart_id=cart.id)


async def delete_movie_from_cart(
        db: AsyncSession,
        user_id: int,
        movie_id: int,
) -> None:
    cart = await get_cart_by_user(db=db, user_id=user_id)
    if cart is None:
        raise EntityNotFound("Cart not found.")

    if not any(item.movie_id == movie_id for item in cart.items):
        raise EntityNotFound("Movie not found.")

    await remove_movie_from_cart(
        db=db,
        cart_id=cart.id,
        movie_id=movie_id
    )


async def add_item_to_cart(
        db: AsyncSession,
        user_id: int,
        movie_id: int,
) -> Cart:

    movie = await get_movie_by_id(db=db, movie_id=movie_id)

    if movie is None:
        raise EntityNotFound("Movie not found.")

    cart = await get_or_create_cart(db=db, user_id=user_id)

    if any(item.movie_id == movie_id for item in cart.items):
        raise EntityAlreadyExists("Movie already in cart.")

    await add_movie_to_cart(
        db=db, cart_id=cart.id, movie_id=movie.id,
    )

    db.expire(cart)

    cart = await get_cart_by_user(db=db, user_id=user_id)

    return cart
