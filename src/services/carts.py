from sqlalchemy.ext.asyncio import AsyncSession

from crud.carts import (
    get_cart_by_user,
    create_cart,
    clear_cart,
    remove_movie_from_cart,
    has_user_purchased_movie, add_movie_to_cart
)
from database.models import Cart, User, UserGroupEnum, Movie
from exceptions.carts import EntityAlreadyExists, DBError, EntityNotFound, StaffRequired, BadRequest
from tasks.emails import send_movie_already_purchased_email_task


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
    user_email: str,
    movie_id: int,
) -> Cart:
    movie = await db.get(Movie, movie_id)
    if movie is None:
        raise EntityNotFound("Movie not found.")

    if await has_user_purchased_movie(db=db, user_id=user_id, movie_id=movie_id):
        send_movie_already_purchased_email_task.delay(user_email, movie.name)
        raise BadRequest("Movie has already been purchased.")

    cart = await get_or_create_cart(db=db, user_id=user_id)

    await add_movie_to_cart(db=db, cart_id=cart.id, movie_id=movie_id)

    db.expire(cart)

    updated_cart = await get_cart_by_user(db=db, user_id=user_id)
    if updated_cart is None:
        raise DBError("Failed to fetch updated cart.")

    return updated_cart


async def moderator_get_cart_by_user_id(
        db: AsyncSession,
        admin: User,
        user_id: int,
) -> Cart:

    if admin.group is None or admin.group.name not in (
            UserGroupEnum.MODERATOR.value,
            UserGroupEnum.ADMIN.value,
    ):
        raise StaffRequired("User must be a moderator or admin.")

    cart = await get_cart_by_user(db=db, user_id=user_id)

    if cart is None:
        raise EntityNotFound("Cart not found.")

    return cart
