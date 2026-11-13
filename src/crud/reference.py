from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Genre, Star, Director, Certification
from schemas.movies import (
    GenreCreateSchema,
    StarCreateSchema,
    DirectorCreateSchema,
    CertificationCreateSchema,
)


async def create_genre(
        db: AsyncSession, genre_data: GenreCreateSchema
) -> Genre:
    genre = Genre(**genre_data.model_dump())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def get_genres(db: AsyncSession) -> Sequence[Genre]:
    stmt = select(Genre).order_by(Genre.id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_star(
        db: AsyncSession, star_data: StarCreateSchema
) -> Star:
    star = Star(**star_data.model_dump())
    db.add(star)
    await db.commit()
    await db.refresh(star)
    return star


async def get_stars(db: AsyncSession) -> Sequence[Star]:
    stmt = select(Star).order_by(Star.id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_director(
        db: AsyncSession, director_data: DirectorCreateSchema
) -> Director:
    director = Director(**director_data.model_dump())
    db.add(director)
    await db.commit()
    await db.refresh(director)
    return director


async def get_directors(db: AsyncSession) -> Sequence[Director]:
    stmt = select(Director).order_by(Director.id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_certification(
        db: AsyncSession, certification_data: CertificationCreateSchema
) -> Certification:
    certification = Certification(**certification_data.model_dump())
    db.add(certification)
    await db.commit()
    await db.refresh(certification)
    return certification


async def get_certifications(db: AsyncSession) -> Sequence[Certification]:
    stmt = select(Certification).order_by(Certification.id)
    result = await db.execute(stmt)
    return result.scalars().all()
