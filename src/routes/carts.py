from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.dependencies import get_current_user
from database import get_db_session
from database.models import User, Cart
from exceptions.carts import EntityNotFound, DBError, EntityAlreadyExists
from schemas.carts import CartResponseSchema, CartItemCreateSchema
from services.carts import get_or_create_cart, clear_user_cart, delete_movie_from_cart, add_item_to_cart

router = APIRouter(prefix="/carts")

ASession = Annotated[AsyncSession, Depends(get_db_session)]
CUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK
)
async def get_user_cart(
        db: ASession,
        current_user: CUser,
) -> Cart | None:
    try:
        return await get_or_create_cart(db=db, user_id=current_user.id)
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except DBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


@router.delete(
    "/items/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_movie_from_my_cart(
        db: ASession,
        current_user: CUser,
        movie_id: int,
) -> None:
    try:
        await delete_movie_from_cart(
            db=db,
            user_id=current_user.id,
            movie_id=movie_id,
        )
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


@router.delete(
    "/items",
    status_code=status.HTTP_204_NO_CONTENT
)
async def clear_my_cart(
        db: ASession,
        current_user: CUser,
) -> None:
    try:
        await clear_user_cart(db=db, user_id=current_user.id)
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


@router.post(
    "/items",
    response_model=CartResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_movie_to_my_cart(
        db: ASession,
        current_user: CUser,
        data: CartItemCreateSchema,
) -> Cart:
    try:
        return await add_item_to_cart(
            db=db,
            user_id=current_user.id,
            movie_id=data.movie_id
        )
    except EntityNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except EntityAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DBError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
