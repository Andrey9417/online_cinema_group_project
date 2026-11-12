from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Genre, Star, Director, Certification
from database.session import get_db_session
from crud.reference import (
    create_genre,
    get_genres,
    create_director,
    get_directors,
    create_certification,
    get_certifications, get_stars, create_star,
)
from schemas.movies import (
    GenreSchema,
    GenreCreateSchema,
    StarSchema,
    StarCreateSchema,
    DirectorSchema,
    DirectorCreateSchema,
    CertificationSchema,
    CertificationCreateSchema,
)

router = APIRouter(tags=["reference"])


@router.post(
    "/genres/",
    response_model=GenreSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_genre(
        genre_data: GenreCreateSchema, db: AsyncSession = Depends(get_db_session)
) -> Genre:
    return await create_genre(db, genre_data)


@router.get("/genres/", response_model=list[GenreSchema])
async def list_genres(
        db: AsyncSession = Depends(get_db_session)
) -> Sequence[Genre]:
    return await get_genres(db)


@router.post(
    "/stars/",
    response_model=StarSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_star(
        star_data: StarCreateSchema, db: AsyncSession = Depends(get_db_session)
) -> Star:
    return await create_star(db, star_data)


@router.get("/stars/", response_model=list[StarSchema])
async def list_stars(
        db: AsyncSession = Depends(get_db_session)
) -> Sequence[Star]:
    return await get_stars(db)


@router.post(
    "/directors/",
    response_model=DirectorSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_director(
        director_data: DirectorCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Director:
    return await create_director(db, director_data)


@router.get("/directors/", response_model=list[DirectorSchema])
async def list_directors(
        db: AsyncSession = Depends(get_db_session)
) -> Sequence[Director]:
    return await get_directors(db)


@router.post(
    "/certifications/",
    response_model=CertificationSchema,
    status_code=status.HTTP_201_CREATED
)
async def add_certification(
        certification_data: CertificationCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Certification:
    return await create_certification(db, certification_data)


@router.get("/certifications/", response_model=list[CertificationSchema])
async def list_certifications(
        db: AsyncSession = Depends(get_db_session)
) -> Sequence[Certification]:
    return await get_certifications(db)
