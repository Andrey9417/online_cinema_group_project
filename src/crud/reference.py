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


async def update_genre(
        db: AsyncSession,
        genre_id: int,
        genre_data: GenreCreateSchema
) -> Genre | None:
    genre = await db.get(Genre, genre_id)

    if genre is None:
        return None

    genre.name = genre_data.name
    await db.commit()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre_id: int) -> bool:
    genre = await db.get(Genre, genre_id)

    if genre is None:
        return False

    await db.delete(genre)
    await db.commit()
    return True


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


async def update_star(
        db: AsyncSession,
        star_id: int,
        star_data: StarCreateSchema
) -> Star | None:
    star = await db.get(Star, star_id)

    if star is None:
        return None

    star.name = star_data.name
    await db.commit()
    await db.refresh(star)
    return star


async def delete_star(db: AsyncSession, star_id: int) -> bool:
    star = await db.get(Star, star_id)

    if star is None:
        return False

    await db.delete(star)
    await db.commit()
    return True


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


async def update_director(
        db: AsyncSession,
        director_id: int,
        director_data: DirectorCreateSchema
) -> Director | None:
    director = await db.get(Director, director_id)

    if director is None:
        return None

    director.name = director_data.name
    await db.commit()
    await db.refresh(director)
    return director


async def delete_director(db: AsyncSession, director_id: int) -> bool:
    director = await db.get(Director, director_id)

    if director is None:
        return False

    await db.delete(director)
    await db.commit()
    return True


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


async def update_certification(
        db: AsyncSession,
        certification_id: int,
        certification_data: CertificationCreateSchema
) -> Certification | None:
    certification = await db.get(Certification, certification_id)

    if certification is None:
        return None

    certification.name = certification_data.name
    await db.commit()
    await db.refresh(certification)
    return certification


async def delete_certification(db: AsyncSession, certification_id: int) -> bool:
    certification = await db.get(Certification, certification_id)

    if certification is None:
        return False

    await db.delete(certification)
    await db.commit()
    return True
