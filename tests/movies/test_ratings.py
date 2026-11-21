import pytest
from sqlalchemy import func, select

from config.dependencies import get_current_user
from database.models.movies import MovieRating
from main import app

API = "/api/v1"


def rating_url(movie_id: int) -> str:
    return f"{API}/movies/{movie_id}/rating/"


def anonymous(client):
    """Drop the auth override so the real get_current_user runs."""
    app.dependency_overrides.pop(get_current_user, None)
    return client


async def saved_rating(db_session, user_id: int, movie_id: int):
    return await db_session.scalar(
        select(MovieRating.rating).where(
            MovieRating.user_id == user_id,
            MovieRating.movie_id == movie_id,
        )
    )


async def test_rate_movie(as_user, db_session, regular_user, make_movie):
    movie = await make_movie()

    response = await as_user(regular_user).put(
        rating_url(movie["id"]), json={"rating": 8}
    )

    assert response.status_code == 200
    assert response.json() == {"detail": "Rating saved."}
    assert await saved_rating(db_session, regular_user.id, movie["id"]) == 8


async def test_rerate_updates_existing(
        as_user, db_session, regular_user, make_movie
):
    movie = await make_movie()
    client = as_user(regular_user)
    await client.put(rating_url(movie["id"]), json={"rating": 3})

    response = await client.put(rating_url(movie["id"]), json={"rating": 9})

    assert response.status_code == 200
    assert await saved_rating(db_session, regular_user.id, movie["id"]) == 9
    count = await db_session.scalar(
        select(func.count()).select_from(MovieRating)
    )
    assert count == 1


@pytest.mark.parametrize("value", [1, 10])
async def test_boundary_ratings_allowed(
        as_user, regular_user, make_movie, value
):
    movie = await make_movie()

    response = await as_user(regular_user).put(
        rating_url(movie["id"]), json={"rating": value}
    )

    assert response.status_code == 200


@pytest.mark.parametrize("value", [0, 11, -5, 100])
async def test_out_of_range_rating_rejected(
        as_user, regular_user, make_movie, value
):
    movie = await make_movie()

    response = await as_user(regular_user).put(
        rating_url(movie["id"]), json={"rating": value}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{}, {"rating": "high"}, {"rating": None}])
async def test_invalid_rating_body(
        as_user, regular_user, make_movie, payload
):
    movie = await make_movie()

    response = await as_user(regular_user).put(
        rating_url(movie["id"]), json=payload
    )

    assert response.status_code == 422


async def test_rate_missing_movie(as_user, regular_user):
    response = await as_user(regular_user).put(
        rating_url(9999), json={"rating": 5}
    )

    assert response.status_code == 404


async def test_rate_requires_auth(client, make_movie):
    movie = await make_movie()

    response = await anonymous(client).put(
        rating_url(movie["id"]), json={"rating": 5}
    )

    assert response.status_code == 401


async def test_ratings_are_per_user(
        as_user, db_session, regular_user, make_user, make_movie
):
    bob = await make_user(email="bob@example.com")
    movie = await make_movie()

    await as_user(regular_user).put(
        rating_url(movie["id"]), json={"rating": 2}
    )
    await as_user(bob).put(rating_url(movie["id"]), json={"rating": 10})

    assert await saved_rating(db_session, regular_user.id, movie["id"]) == 2
    assert await saved_rating(db_session, bob.id, movie["id"]) == 10


async def test_remove_rating(as_user, db_session, regular_user, make_movie):
    movie = await make_movie()
    client = as_user(regular_user)
    await client.put(rating_url(movie["id"]), json={"rating": 7})

    response = await client.delete(rating_url(movie["id"]))

    assert response.status_code == 204
    assert await saved_rating(db_session, regular_user.id, movie["id"]) is None


async def test_remove_missing_rating(as_user, regular_user, make_movie):
    movie = await make_movie()

    response = await as_user(regular_user).delete(rating_url(movie["id"]))

    assert response.status_code == 404


async def test_remove_rating_requires_auth(client, make_movie):
    movie = await make_movie()

    response = await anonymous(client).delete(rating_url(movie["id"]))

    assert response.status_code == 401


async def test_remove_does_not_touch_other_users(
        as_user, db_session, regular_user, make_user, make_movie
):
    bob = await make_user(email="bob@example.com")
    movie = await make_movie()
    await as_user(regular_user).put(
        rating_url(movie["id"]), json={"rating": 4}
    )
    await as_user(bob).put(rating_url(movie["id"]), json={"rating": 6})

    await as_user(regular_user).delete(rating_url(movie["id"]))

    assert await saved_rating(db_session, regular_user.id, movie["id"]) is None
    assert await saved_rating(db_session, bob.id, movie["id"]) == 6
