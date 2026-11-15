from collections.abc import Sequence

from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import require_moderator
from database.models import Genre, Star, Director, Certification, User
from database.session import get_db_session
from crud.reference import (
    get_genre_by_id,
    get_genres,
    create_genre,
    update_genre,
    delete_genre,
    get_star_by_id,
    get_stars,
    create_star,
    update_star,
    delete_star,
    get_director_by_id,
    get_directors,
    create_director,
    update_director,
    delete_director,
    get_certification_by_id,
    get_certifications,
    create_certification,
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


# ---------- genres ----------
@router.get("/genres/", response_model=list[GenreSchema])
async def list_genres(
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Genre]:
    return await get_genres(db)


@router.post(
    "/genres/",
    response_model=GenreSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_genre(
        data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Genre:
    genre = await create_genre(db, data.name)
    if genre is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Genre with this name already exists.",
        )
    return genre


@router.put("/genres/{genre_id}/", response_model=GenreSchema)
async def edit_genre(
        genre_id: int,
        data: GenreCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Genre:
    genre = await get_genre_by_id(db, genre_id)
    if genre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found.",
        )
    if not await update_genre(db, genre, data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Genre with this name already exists.",
        )
    return genre


@router.delete("/genres/{genre_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_genre(
        genre_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Response:
    if not await delete_genre(db, genre_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- stars ----------
@router.get("/stars/", response_model=list[StarSchema])
async def list_stars(
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Star]:
    return await get_stars(db)


@router.post(
    "/stars/",
    response_model=StarSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_star(
        data: StarCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Star:
    star = await create_star(db, data.name)
    if star is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Star with this name already exists.",
        )
    return star


@router.put("/stars/{star_id}/", response_model=StarSchema)
async def edit_star(
        star_id: int,
        data: StarCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Star:
    star = await get_star_by_id(db, star_id)
    if star is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found.",
        )
    if not await update_star(db, star, data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Star with this name already exists.",
        )
    return star


@router.delete("/stars/{star_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_star(
        star_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Response:
    if not await delete_star(db, star_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- directors ----------
@router.get("/directors/", response_model=list[DirectorSchema])
async def list_directors(
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Director]:
    return await get_directors(db)


@router.post(
    "/directors/",
    response_model=DirectorSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_director(
        data: DirectorCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Director:
    director = await create_director(db, data.name)
    if director is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Director with this name already exists.",
        )
    return director


@router.put("/directors/{director_id}/", response_model=DirectorSchema)
async def edit_director(
        director_id: int,
        data: DirectorCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Director:
    director = await get_director_by_id(db, director_id)
    if director is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found.",
        )
    if not await update_director(db, director, data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Director with this name already exists.",
        )
    return director


@router.delete(
    "/directors/{director_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_director(
        director_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Response:
    if not await delete_director(db, director_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- certifications ----------
@router.get("/certifications/", response_model=list[CertificationSchema])
async def list_certifications(
        db: AsyncSession = Depends(get_db_session),
) -> Sequence[Certification]:
    return await get_certifications(db)


@router.post(
    "/certifications/",
    response_model=CertificationSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_certification(
        data: CertificationCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Certification:
    certification = await create_certification(db, data.name)
    if certification is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certification with this name already exists.",
        )
    return certification


@router.put(
    "/certifications/{certification_id}/",
    response_model=CertificationSchema,
)
async def edit_certification(
        certification_id: int,
        data: CertificationCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Certification:
    certification = await get_certification_by_id(db, certification_id)
    if certification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found.",
        )
    if not await update_certification(db, certification, data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certification with this name already exists.",
        )
    return certification


@router.delete(
    "/certifications/{certification_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_certification(
        certification_id: int,
        db: AsyncSession = Depends(get_db_session),
        moderator: User = Depends(require_moderator),
) -> Response:
    if not await delete_certification(db, certification_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
