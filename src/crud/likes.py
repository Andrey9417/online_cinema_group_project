from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MovieLike
from schemas.likes import MovieLikeCreateSchema, MovieReactionsSchema


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
