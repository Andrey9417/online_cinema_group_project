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
