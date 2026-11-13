import math
from database.session import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

# get_db: той самий імпорт, що використовується в проєкті (де він оголошений, там і беріть)
# CRUD-функції імпортуйте з файлу, який ви мені скинули (наприклад, from crud import movies as crud)
from schemas.movies import (
    MovieCreateSchema,
    MovieUpdateSchema,
    MovieDetailSchema,        # ПІДСТАВТЕ свої назви response-схем із schemas/movies.py
    MovieListResponseSchema,  # (я їх не бачив, ці дві назви умовні)
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def list_movies(
    page: int = Query(1, ge=1),                 # номер сторінки, мінімум 1 (ge = "більше або дорівнює")
    per_page: int = Query(10, ge=1, le=20),     # скільки фільмів на сторінці, обмежуємо зверху, щоб не віддавати все одразу
    db: AsyncSession = Depends(get_db),         # сесія БД на час запиту
):
    movies, total_items = await crud.get_movie_list(db, page, per_page)  # CRUD повертає кортеж: (список, загальна кількість)

    if not movies:
        # сторінка порожня (або фільмів немає взагалі)
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = math.ceil(total_items / per_page)  # округлюємо вгору: 25 фільмів по 10 це 3 сторінки

    return {
        "movies": movies,
        "prev_page": f"/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await crud.get_movie_by_id(db, movie_id)  # тут уже є joinedload, тож жанри/актори підтягнуться
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found.")
    return movie


@router.post("/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(movie_data: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    movie = await crud.create_movie(db, movie_data)
    # створений об'єкт не має завантажених зв'язків (genres тощо); у async-сесії
    # їх ліниве читання при серіалізації впаде з MissingGreenlet,
    # тому перечитуємо фільм через get_movie_by_id, який робить joinedload
    return await crud.get_movie_by_id(db, movie.id)


@router.patch("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def update_movie(movie_id: int, movie_data: MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    movie = await crud.update_movie(db, movie_id, movie_data)  # None, якщо такого фільму немає
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found.")
    return movie


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_movie(db, movie_id)  # True/False: чи був що видаляти
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)