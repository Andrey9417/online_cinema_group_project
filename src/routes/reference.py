from collections.abc import Sequence

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Genre, Star, Director, Certification
from database.session import get_db_session
from crud.reference import (
    create_genre,
    get_genres,
    create_director,
    get_directors,
    create_certification,
    get_certifications,
    get_stars,
    create_star,
    delete_genre,
    update_genre,
    update_star,
    delete_star,
    update_director,
    delete_director,
    update_certification,
    delete_certification,
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
        genre_data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Genre:
    return await create_genre(db, genre_data)


@router.get("/genres/", response_model=list[GenreSchema])
async def list_genres(
        db: AsyncSession = Depends(get_db_session)
) -> Sequence[Genre]:
    return await get_genres(db)


@router.put(
    "/genres/{genre_id}/",
    response_model=GenreSchema,
)
async def put_genre(
        genre_id: int,
        genre_data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Genre:
    genre = await update_genre(db, genre_id, genre_data)

    if genre is None:
        raise HTTPException(404, "Genre not found")
    return genre


@router.delete("/genres/{genre_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_genre(
        genre_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await delete_genre(db, genre_id)
    if not deleted:
        raise HTTPException(404, "Genre not found")


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


@router.put(
    "/stars/{star_id}/",
    response_model=StarSchema,
)
async def put_star(
        star_id: int,
        star_data: StarCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Star:
    star = await update_star(db, star_id, star_data)

    if star is None:
        raise HTTPException(404, "Star not found")
    return star


@router.delete("/stars/{star_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_star(
        star_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await delete_star(db, star_id)
    if not deleted:
        raise HTTPException(404, "Star not found")


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


@router.put(
    "/directors/{director_id}/",
    response_model=DirectorSchema,
)
async def put_director(
        director_id: int,
        director_data: DirectorCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Director:
    director = await update_director(db, director_id, director_data)

    if director is None:
        raise HTTPException(404, "Director not found")
    return director


@router.delete("/directors/{director_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_director(
        director_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await delete_director(db, director_id)
    if not deleted:
        raise HTTPException(404, "Director not found")


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


@router.put(
    "/certifications/{certification_id}/",
    response_model=CertificationSchema,
)
async def put_certification(
        certification_id: int,
        certification_data: CertificationCreateSchema,
        db: AsyncSession = Depends(get_db_session)
) -> Certification:
    certification = await update_certification(db, certification_id, certification_data)

    if certification is None:
        raise HTTPException(404, "Certification not found")
    return certification


@router.delete("/certifications/{certification_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_certification(
        certification_id: int,
        db: AsyncSession = Depends(get_db_session),
) -> None:
    deleted = await delete_certification(db, certification_id)
    if not deleted:
        raise HTTPException(404, "Certification not found")
