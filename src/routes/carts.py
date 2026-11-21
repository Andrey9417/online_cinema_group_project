from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.dependencies import get_current_user
from database import get_db_session
from database.models import User, Cart
from exceptions.carts import EntityNotFound, DBError, EntityAlreadyExists, StaffRequired, BadRequest
from schemas.carts import CartResponseSchema, CartItemCreateSchema
from services.carts import get_or_create_cart, clear_user_cart, delete_movie_from_cart, add_item_to_cart, \
    moderator_get_cart_by_user_id

router = APIRouter(prefix="/carts", tags=["carts"])

ASession = Annotated[AsyncSession, Depends(get_db_session)]
CUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get my cart",
    description=(
        "Returns the cart of the authenticated user together with all its items "
        "and their movies. If the user does not have a cart yet, an empty cart "
        "is created and returned."
    ),
    responses={
        401: {"description": "Not authenticated."},
        404: {"description": "User not found."},
        500: {"description": "Failed to retrieve or create the cart."},
    },
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


@router.get(
    "/users/{user_id}",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a user's cart (staff only)",
    description=(
        "Returns the cart of the user with the given id. Available only to "
        "moderators and admins. Unlike `GET /carts/`, it never creates a cart."
    ),
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "The current user is not a moderator or admin."},
        404: {"description": "The user has no cart."},
        422: {"description": "`user_id` must be a positive integer."},
    },
)
async def staff_get_user_cart(
        db: ASession,
        admin: CUser,
        user_id: Annotated[
            int,
            Path(gt=0, description="Id of the user whose cart is requested."),
        ],
) -> Cart:
    try:
        cart = await moderator_get_cart_by_user_id(
            db=db, admin=admin, user_id=user_id
        )
    except StaffRequired as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        ) from e
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e

    return cart


@router.delete(
    "/items/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a movie from my cart",
    description="Removes a single movie from the cart of the authenticated user.",
    responses={
        401: {"description": "Not authenticated."},
        404: {"description": "The user has no cart, or the movie is not in the cart."},
        422: {"description": "`movie_id` must be an integer."},
    },
)
async def delete_movie_from_my_cart(
        db: ASession,
        current_user: CUser,
        movie_id: Annotated[
            int,
            Path(description="Id of the movie to remove from the cart."),
        ],
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear my cart",
    description=(
        "Removes all items from the cart of the authenticated user. "
        "The cart itself is kept."
    ),
    responses={
        401: {"description": "Not authenticated."},
        404: {"description": "The user has no cart."},
    },
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
    summary="Add a movie to my cart",
    description=(
        "Adds a movie to the cart of the authenticated user and returns the "
        "updated cart. The cart is created automatically if it does not exist. "
        "If the user has already purchased the movie, it is not added and a "
        "notification email is sent."
    ),
    responses={
        400: {"description": "The movie has already been purchased by the user."},
        401: {"description": "Not authenticated."},
        404: {"description": "The movie does not exist."},
        409: {"description": "The movie is already in the cart."},
        422: {"description": "Invalid request body."},
        500: {"description": "Unexpected database error."},
    },
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
            movie_id=data.movie_id,
            user_email=current_user.email
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
    except BadRequest as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except DBError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
