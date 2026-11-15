from collections.abc import Sequence

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Genre, Star, Director, Certification


# ---------- genres ----------
async def get_genre_by_id(db: AsyncSession, genre_id: int) -> Genre | None:
    return await db.get(Genre, genre_id)


async def get_genres(db: AsyncSession) -> Sequence[Genre]:
    result = await db.execute(select(Genre).order_by(Genre.id))
    return result.scalars().all()


async def create_genre(db: AsyncSession, name: str) -> Genre | None:
    genre = Genre(name=name)
    db.add(genre)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre: Genre, name: str) -> bool:
    genre.name = name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    await db.refresh(genre)
    return True


async def delete_genre(db: AsyncSession, genre_id: int) -> bool:
    result = await db.execute(delete(Genre).where(Genre.id == genre_id))
    await db.commit()
    return result.rowcount > 0


# ---------- stars ----------
async def get_star_by_id(db: AsyncSession, star_id: int) -> Star | None:
    return await db.get(Star, star_id)


async def get_stars(db: AsyncSession) -> Sequence[Star]:
    result = await db.execute(select(Star).order_by(Star.id))
    return result.scalars().all()


async def create_star(db: AsyncSession, name: str) -> Star | None:
    star = Star(name=name)
    db.add(star)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(star)
    return star


async def update_star(db: AsyncSession, star: Star, name: str) -> bool:
    star.name = name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    await db.refresh(star)
    return True


async def delete_star(db: AsyncSession, star_id: int) -> bool:
    result = await db.execute(delete(Star).where(Star.id == star_id))
    await db.commit()
    return result.rowcount > 0


# ---------- directors ----------
async def get_director_by_id(
        db: AsyncSession, director_id: int
) -> Director | None:
    return await db.get(Director, director_id)


async def get_directors(db: AsyncSession) -> Sequence[Director]:
    result = await db.execute(select(Director).order_by(Director.id))
    return result.scalars().all()


async def create_director(db: AsyncSession, name: str) -> Director | None:
    director = Director(name=name)
    db.add(director)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(director)
    return director


async def update_director(
        db: AsyncSession, director: Director, name: str
) -> bool:
    director.name = name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    await db.refresh(director)
    return True


async def delete_director(db: AsyncSession, director_id: int) -> bool:
    result = await db.execute(
        delete(Director).where(Director.id == director_id)
    )
    await db.commit()
    return result.rowcount > 0


# ---------- certifications ----------
async def get_certification_by_id(
        db: AsyncSession, certification_id: int
) -> Certification | None:
    return await db.get(Certification, certification_id)


async def get_certifications(db: AsyncSession) -> Sequence[Certification]:
    result = await db.execute(select(Certification).order_by(Certification.id))
    return result.scalars().all()


async def create_certification(
        db: AsyncSession, name: str
) -> Certification | None:
    certification = Certification(name=name)
    db.add(certification)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(certification)
    return certification


async def update_certification(
        db: AsyncSession, certification: Certification, name: str
) -> bool:
    certification.name = name
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    await db.refresh(certification)
    return True


async def delete_certification(db: AsyncSession, certification_id: int) -> bool:
    result = await db.execute(
        delete(Certification).where(Certification.id == certification_id)
    )
    await db.commit()
    return result.rowcount > 0
