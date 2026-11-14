from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieLike, CommentLike
from schemas.likes import (
    MovieLikeCreateSchema,
    MovieReactionsSchema,
    CommentLikeCreateSchema,
    CommentReactionsSchema
)


async def set_movie_reaction(
        db: AsyncSession,
        movie_id: int,
        user_id: int,
        like_data: MovieLikeCreateSchema
) -> MovieLike:
    stmt = select(MovieLike).where(
        MovieLike.user_id == user_id,
        MovieLike.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    like = result.scalar_one_or_none()

    if not like:
        like = MovieLike(
            **like_data.model_dump(),
            movie_id=movie_id,
            user_id=user_id,
        )
        db.add(like)
    else:
        like.is_like = like_data.is_like

    await db.commit()
    await db.refresh(like)

    return like


async def get_movie_reactions(
        db: AsyncSession,
        movie_id: int
) -> MovieReactionsSchema:
    stmt = (
        select(MovieLike.is_like, func.count())
        .where(MovieLike.movie_id == movie_id)
        .group_by(MovieLike.is_like)
    )
    result = await db.execute(stmt)
    rows = result.all()

    counts = {is_like: count for is_like, count in rows}
    likes = counts.get(True, 0)
    dislikes = counts.get(False, 0)

    return MovieReactionsSchema(likes=likes, dislikes=dislikes)


async def delete_movie_reaction(
        db: AsyncSession,
        movie_id: int,
        user_id: int,
) -> bool:
    stmt = select(MovieLike).where(
        MovieLike.user_id == user_id,
        MovieLike.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    like = result.scalar_one_or_none()

    if not like:
        return False

    await db.delete(like)
    await db.commit()
    return True


async def set_comment_reaction(
        db: AsyncSession,
        user_id: int,
        comment_id: int,
        reaction_data: CommentLikeCreateSchema,
) -> CommentLike:
    stmt = select(CommentLike).where(
        CommentLike.user_id == user_id,
        CommentLike.comment_id == comment_id,
    )
    result = await db.execute(stmt)
    reaction = result.scalar_one_or_none()

    if reaction is None:
        reaction = CommentLike(
            user_id=user_id,
            comment_id=comment_id,
            is_like=reaction_data.is_like,
        )
        db.add(reaction)
    else:
        reaction.is_like = reaction_data.is_like

    await db.commit()
    await db.refresh(reaction)
    return reaction


async def delete_comment_reaction(
        db: AsyncSession,
        user_id: int,
        comment_id: int,
) -> bool:
    stmt = select(CommentLike).where(
        CommentLike.user_id == user_id,
        CommentLike.comment_id == comment_id,
    )
    result = await db.execute(stmt)
    reaction = result.scalar_one_or_none()

    if reaction is None:
        return False

    await db.delete(reaction)
    await db.commit()
    return True


async def get_comment_reactions(
        db: AsyncSession,
        comment_id: int,
) -> CommentReactionsSchema:
    stmt = (
        select(CommentLike.is_like, func.count())
        .where(CommentLike.comment_id == comment_id)
        .group_by(CommentLike.is_like)
    )
    result = await db.execute(stmt)
    counts = {is_like: count for is_like, count in result.all()}
    return CommentReactionsSchema(
        likes=counts.get(True, 0),
        dislikes=counts.get(False, 0),
    )
