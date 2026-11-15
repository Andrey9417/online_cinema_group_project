from collections.abc import Sequence
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from config.dependencies import get_current_user
from crud.comments import (
    create_reply,
    create_comment,
    get_movie_comments,
    get_comment,
    update_comment,
    delete_comment,
)
from crud.movies import get_movie_by_id
from database.models import User, Comment, CommentLike
from database.session import get_db_session
from schemas.comments import CommentCreateSchema, CommentSchema
from crud.likes import (
    set_comment_reaction,
    delete_comment_reaction,
    get_comment_reactions,
)
from schemas.likes import (
    CommentLikeCreateSchema,
    CommentLikeSchema,
    CommentReactionsSchema,
)
from tasks.emails import (
    send_comment_reply_email_task,
    send_comment_like_email_task,
)

router = APIRouter(tags=["comments"])


@router.post(
    "/movies/{movie_id}/comments/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a movie",
    responses={404: {"description": "Movie not found"}},
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
    response_model=list[CommentSchema],
    summary="List movie comments",
)
async def list_comments(
        movie_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Comment]:
    return await get_movie_comments(db, movie_id)


@router.post(
    "/comments/{comment_id}/reply/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to a comment",
    responses={404: {"description": "Parent comment not found"}},
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
    parent = await get_comment(db, comment_id)
    if parent.user_id != current_user.id:
        author = await db.get(User, parent.user_id)
        send_comment_reply_email_task.delay(
            author.email, parent.text, reply.text
        )
    return reply


@router.put(
    "/comments/{comment_id}/",
    response_model=CommentSchema,
    summary="Edit a comment",
    description="Only the comment's author can edit it.",
    responses={
        403: {"description": "Not the comment's author"},
        404: {"description": "Comment not found"},
    },
)
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


@router.delete(
    "/comments/{comment_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="Only the comment's author can delete it.",
    responses={
        403: {"description": "Not the comment's author"},
        404: {"description": "Comment not found"},
    },
)
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


@router.post(
    "/comments/{comment_id}/reactions/",
    response_model=CommentLikeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Like or dislike a comment",
    responses={404: {"description": "Comment not found"}},
)
async def set_comment_like(
        comment_id: int,
        reaction_data: CommentLikeCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
) -> CommentLike:
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    reaction = await set_comment_reaction(
        db, current_user.id, comment_id, reaction_data
    )

    if reaction.is_like and comment.user_id != current_user.id:
        author = await db.get(User, comment.user_id)
        send_comment_like_email_task.delay(author.email, comment.text)

    return reaction


@router.delete(
    "/comments/{comment_id}/reactions/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove comment reaction",
    responses={404: {"description": "Reaction not found"}},
)
async def delete_comment_like(
        comment_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
) -> Response:
    deleted = await delete_comment_reaction(
        db, current_user.id, comment_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/comments/{comment_id}/reactions/",
    response_model=CommentReactionsSchema,
    summary="Get comment like/dislike counts",
    responses={404: {"description": "Comment not found"}},
)
async def comment_reactions(
        comment_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> CommentReactionsSchema:
    comment = await get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    return await get_comment_reactions(db, comment_id)
