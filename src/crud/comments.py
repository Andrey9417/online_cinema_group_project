from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Comment

from schemas.comments import CommentCreateSchema


async def create_comment(
        db: AsyncSession,
        movie_id: int,
        user_id: int,
        comment_data: CommentCreateSchema
) -> Comment:
    comment = Comment(
        **comment_data.model_dump(),
        movie_id=movie_id,
        user_id=user_id
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment


async def get_movie_comments(
        db: AsyncSession,
        movie_id: int
) -> Sequence[Comment]:
    stmt = (
        select(Comment)
        .where(Comment.movie_id == movie_id)
        .order_by(Comment.created_at.desc())
    )

    result = await db.execute(stmt)
    comments = result.scalars().all()

    return comments


async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    return await db.get(Comment, comment_id)


async def update_comment(
    db: AsyncSession, comment: Comment, comment_data: CommentCreateSchema
) -> Comment:
    comment.text = comment_data.text
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    await db.delete(comment)
    await db.commit()


async def create_reply(
    db: AsyncSession,
    parent_comment_id: int,
    user_id: int,
    comment_data: CommentCreateSchema,
) -> Comment | None:
    parent = await db.get(Comment, parent_comment_id)

    if parent is None:
        return None

    reply = Comment(
        movie_id=parent.movie_id,
        user_id=user_id,
        parent_id=parent.id,
        text=comment_data.text,
    )

    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    return reply
