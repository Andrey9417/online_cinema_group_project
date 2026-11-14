from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from database.models import Cart, CartItem
from exceptions.carts import DBError, EntityNotFound, PgErrorCode, EntityAlreadyExists


async def get_cart_by_user(db: AsyncSession, user_id: int) -> Cart | None:
    stmt = (
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_cart_item(
        db: AsyncSession,
        cart_id: int,
        movie_id: int
) -> CartItem | None:
    stmt = (
        select(CartItem)
        .where(
            CartItem.cart_id == cart_id,
            CartItem.movie_id == movie_id
            )
        .options(joinedload(CartItem.movie))
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def add_movie_to_cart(
        db: AsyncSession,
        cart_id: int,
        movie_id: int,
) -> CartItem:

    item = CartItem(cart_id=cart_id, movie_id=movie_id)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        sqlstate = getattr(e.orig, "sqlstate", None)

        if sqlstate == PgErrorCode.UNIQUE_VIOLATION:
            raise EntityAlreadyExists("Movie already exists.") from e

        if sqlstate == PgErrorCode.FOREIGN_KEY_VIOLATION:
            raise EntityNotFound("Movie or cart not found.") from e

        raise DBError("Unexpected database integrity error") from e

    created_item = await get_cart_item(db, cart_id, movie_id)
    if created_item is None:
        raise DBError("Failed to fetch created cart item.")
    return created_item


async def create_cart(db: AsyncSession, user_id: int) -> Cart:
    new_cart = Cart(user_id=user_id)

    db.add(new_cart)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        sqlstate = getattr(e.orig, "sqlstate", None)
        if sqlstate == PgErrorCode.UNIQUE_VIOLATION:
            raise EntityAlreadyExists("Cart already exists.") from e
        if sqlstate == PgErrorCode.FOREIGN_KEY_VIOLATION:
            raise EntityNotFound("User not found.") from e

        raise DBError("Unexpected database integrity error.") from e

    created_cart = await get_cart_by_user(db, user_id)
    if created_cart is None:
        raise DBError("Failed to fetch created cart.")

    return created_cart


async def delete_cart(db: AsyncSession, cart: Cart) -> None:
    await db.delete(cart)
    await db.commit()


async def remove_movie_from_cart(
        db: AsyncSession,
        cart_id: int,
        movie_id: int
) -> bool:
    stmt = delete(CartItem).where(
        CartItem.cart_id == cart_id,
        CartItem.movie_id == movie_id
    )

    res = await db.execute(stmt)
    await db.commit()
    return (res.rowcount or 0) > 0


async def clear_cart(db: AsyncSession, cart_id: int) -> None:
    stmt = delete(CartItem).where(CartItem.cart_id == cart_id)

    await db.execute(stmt)
    await db.commit()


async def is_movie_in_any_cart(db: AsyncSession, movie_id: int) -> bool:
    stmt = select(CartItem.id).where(CartItem.movie_id == movie_id).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
