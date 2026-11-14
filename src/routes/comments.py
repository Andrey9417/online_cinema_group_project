from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from crud.comments import create_reply, create_comment, get_movie_comments, get_comment, update_comment, delete_comment
from crud.movies import get_movie_by_id
from database.models import User, Comment
from database.session import get_db_session
from schemas.comments import CommentCreateSchema, CommentSchema

router = APIRouter(tags=["comments"])


@router.post(
    "/movies/{movie_id}/comments/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_comment(
        movie_id: int,
        comment_data: CommentCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
) -> Comment:
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return await create_comment(db, movie_id, current_user.id, comment_data)


@router.get(
    "/movies/{movie_id}/comments/",
    response_model=list[CommentSchema]
)
async def list_comments(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Comment]:
    return await get_movie_comments(db, movie_id)


@router.post(
    "/comments/{comment_id}/reply/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_reply(
        comment_id: int,
        comment_data: CommentCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
) -> Comment:
    reply = await create_reply(db, comment_id, current_user.id, comment_data)
    if reply is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return reply


@router.put("/comments/{comment_id}/", response_model=CommentSchema)
async def edit_comment(
        comment_id: int,
        comment_data: CommentCreateSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
) -> Comment:
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(403, "Not your comment")
    return await update_comment(db, comment, comment_data)


@router.delete("/comments/{comment_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment(
        comment_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
) -> None:
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(403, "Not your comment")
    await delete_comment(db, comment)
