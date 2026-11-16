from config.dependencies import get_current_user
from main import app

API = "/api/v1"
FAV = f"{API}/movies/favorites/"


def fav_url(movie_id: int) -> str:
    return f"{API}/movies/{movie_id}/favorite/"


def anonymous(client):
    """Drop the auth override so the real get_current_user runs."""
    app.dependency_overrides.pop(get_current_user, None)
    return client


async def favorite(as_user, user, *movies):
    for movie in movies:
        response = await as_user(user).post(fav_url(movie["id"]))
        assert response.status_code == 201, response.text


def names(response) -> list[str]:
    return [m["name"] for m in response.json()["movies"]]


async def test_add_to_favorites(as_user, regular_user, make_movie):
    movie = await make_movie()

    response = await as_user(regular_user).post(fav_url(movie["id"]))

    assert response.status_code == 201
    assert response.json() == {"detail": "Movie added to favorites."}


async def test_added_movie_appears_in_list(
        as_user, regular_user, make_movie
):
    movie = await make_movie(name="Alien")
    await favorite(as_user, regular_user, movie)

    response = await as_user(regular_user).get(FAV)

    assert response.status_code == 200
    assert names(response) == ["Alien"]
    assert response.json()["total_items"] == 1


async def test_add_twice_conflict(as_user, regular_user, make_movie):
    movie = await make_movie()
    await favorite(as_user, regular_user, movie)

    response = await as_user(regular_user).post(fav_url(movie["id"]))

    assert response.status_code == 409


async def test_add_missing_movie(as_user, regular_user):
    response = await as_user(regular_user).post(fav_url(9999))

    assert response.status_code == 404


async def test_add_requires_auth(client, make_movie):
    movie = await make_movie()

    response = await anonymous(client).post(fav_url(movie["id"]))

    assert response.status_code == 401


async def test_remove_from_favorites(as_user, regular_user, make_movie):
    movie = await make_movie()
    await favorite(as_user, regular_user, movie)

    response = await as_user(regular_user).delete(fav_url(movie["id"]))

    assert response.status_code == 204
    after = await as_user(regular_user).get(FAV)
    assert after.json()["total_items"] == 0


async def test_remove_not_in_favorites(as_user, regular_user, make_movie):
    movie = await make_movie()

    response = await as_user(regular_user).delete(fav_url(movie["id"]))

    assert response.status_code == 404


async def test_remove_requires_auth(client, make_movie):
    movie = await make_movie()

    response = await anonymous(client).delete(fav_url(movie["id"]))

    assert response.status_code == 401


async def test_list_requires_auth(client):
    response = await anonymous(client).get(FAV)

    assert response.status_code == 401


async def test_list_empty(as_user, regular_user):
    response = await as_user(regular_user).get(FAV)

    assert response.status_code == 200
    body = response.json()
    assert body["movies"] == []
    assert body["total_items"] == 0
    assert body["total_pages"] == 0


async def test_favorites_are_per_user(
        as_user, regular_user, make_user, make_movie
):
    bob = await make_user(email="bob@example.com")
    first = await make_movie(name="First")
    second = await make_movie(name="Second")
    await favorite(as_user, regular_user, first)
    await favorite(as_user, bob, second)

    response = await as_user(regular_user).get(FAV)

    assert names(response) == ["First"]


async def test_search_by_title(as_user, regular_user, make_movie):
    alien = await make_movie(name="Alien")
    heat = await make_movie(name="Heat")
    await favorite(as_user, regular_user, alien, heat)

    response = await as_user(regular_user).get(FAV, params={"search": "ali"})

    assert names(response) == ["Alien"]


async def test_search_by_description(as_user, regular_user, make_movie):
    one = await make_movie(name="One", description="A space horror story")
    two = await make_movie(name="Two", description="A bank robbery")
    await favorite(as_user, regular_user, one, two)

    response = await as_user(regular_user).get(
        FAV, params={"search": "SPACE"}
    )

    assert names(response) == ["One"]


async def test_search_by_star(as_user, regular_user, make_movie):
    with_star = await make_movie(name="With star")
    without = await make_movie(name="Without", star_ids=[])
    await favorite(as_user, regular_user, with_star, without)

    response = await as_user(regular_user).get(
        FAV, params={"search": "keanu"}
    )

    assert names(response) == ["With star"]


async def test_search_by_director(as_user, regular_user, make_movie):
    with_director = await make_movie(name="With director")
    without = await make_movie(name="Without", director_ids=[])
    await favorite(as_user, regular_user, with_director, without)

    response = await as_user(regular_user).get(
        FAV, params={"search": "stahelski"}
    )

    assert names(response) == ["With director"]


async def test_search_only_inside_favorites(
        as_user, regular_user, make_movie
):
    await make_movie(name="Alien")

    response = await as_user(regular_user).get(
        FAV, params={"search": "alien"}
    )

    assert response.json()["total_items"] == 0


async def test_filter_by_year(as_user, regular_user, make_movie):
    old = await make_movie(name="Old", year=1990)
    new = await make_movie(name="New", year=2020)
    await favorite(as_user, regular_user, old, new)

    response = await as_user(regular_user).get(FAV, params={"year": 1990})

    assert names(response) == ["Old"]


async def test_filter_by_min_imdb(as_user, regular_user, make_movie):
    low = await make_movie(name="Low", imdb=5.0)
    high = await make_movie(name="High", imdb=8.5)
    exact = await make_movie(name="Exact", imdb=7.0)
    await favorite(as_user, regular_user, low, high, exact)

    response = await as_user(regular_user).get(
        FAV, params={"min_imdb": 7.0, "sort_by": "imdb", "order": "asc"}
    )

    assert names(response) == ["Exact", "High"]


async def test_filters_combine(as_user, regular_user, make_movie):
    a = await make_movie(name="A", year=2000, imdb=9.0)
    b = await make_movie(name="B", year=2000, imdb=5.0)
    c = await make_movie(name="C", year=2010, imdb=9.0)
    await favorite(as_user, regular_user, a, b, c)

    response = await as_user(regular_user).get(
        FAV, params={"year": 2000, "min_imdb": 8}
    )

    assert names(response) == ["A"]


async def test_default_sort_is_year_desc(as_user, regular_user, make_movie):
    a = await make_movie(name="A", year=1990)
    b = await make_movie(name="B", year=2020)
    c = await make_movie(name="C", year=2005)
    await favorite(as_user, regular_user, a, b, c)

    response = await as_user(regular_user).get(FAV)

    assert names(response) == ["B", "C", "A"]


async def test_sort_by_year_asc(as_user, regular_user, make_movie):
    a = await make_movie(name="A", year=1990)
    b = await make_movie(name="B", year=2020)
    await favorite(as_user, regular_user, a, b)

    response = await as_user(regular_user).get(
        FAV, params={"sort_by": "year", "order": "asc"}
    )

    assert names(response) == ["A", "B"]


async def test_sort_by_imdb_desc(as_user, regular_user, make_movie):
    a = await make_movie(name="A", imdb=6.0)
    b = await make_movie(name="B", imdb=9.0)
    c = await make_movie(name="C", imdb=7.5)
    await favorite(as_user, regular_user, a, b, c)

    response = await as_user(regular_user).get(
        FAV, params={"sort_by": "imdb", "order": "desc"}
    )

    assert names(response) == ["B", "C", "A"]


async def test_sort_by_price_asc(as_user, regular_user, make_movie):
    a = await make_movie(name="A", price="30.00")
    b = await make_movie(name="B", price="5.00")
    c = await make_movie(name="C", price="12.50")
    await favorite(as_user, regular_user, a, b, c)

    response = await as_user(regular_user).get(
        FAV, params={"sort_by": "price", "order": "asc"}
    )

    assert names(response) == ["B", "C", "A"]


async def test_sort_by_popularity_uses_votes(
        as_user, regular_user, make_movie
):
    a = await make_movie(name="A", votes=10)
    b = await make_movie(name="B", votes=5000)
    c = await make_movie(name="C", votes=300)
    await favorite(as_user, regular_user, a, b, c)

    response = await as_user(regular_user).get(
        FAV, params={"sort_by": "popularity", "order": "desc"}
    )

    assert names(response) == ["B", "C", "A"]


async def test_invalid_sort_field(as_user, regular_user):
    response = await as_user(regular_user).get(
        FAV, params={"sort_by": "color"}
    )

    assert response.status_code == 422


async def test_invalid_order(as_user, regular_user):
    response = await as_user(regular_user).get(
        FAV, params={"order": "sideways"}
    )

    assert response.status_code == 422


async def test_pagination(as_user, regular_user, make_movie):
    movies = [
        await make_movie(name=f"M{i}", year=2000 + i) for i in range(3)
    ]
    await favorite(as_user, regular_user, *movies)
    params = {"per_page": 2, "sort_by": "year", "order": "asc"}

    first = await as_user(regular_user).get(FAV, params=params)
    second = await as_user(regular_user).get(
        FAV, params={**params, "page": 2}
    )

    body = first.json()
    assert names(first) == ["M0", "M1"]
    assert body["total_items"] == 3
    assert body["total_pages"] == 2
    assert body["prev_page"] is None
    assert body["next_page"] is not None
    assert names(second) == ["M2"]
    assert second.json()["prev_page"] is not None
    assert second.json()["next_page"] is None


async def test_page_beyond_last_is_empty(as_user, regular_user, make_movie):
    movie = await make_movie()
    await favorite(as_user, regular_user, movie)

    response = await as_user(regular_user).get(FAV, params={"page": 5})

    assert response.status_code == 200
    assert response.json()["movies"] == []
    assert response.json()["total_items"] == 1


async def test_pagination_limits(as_user, regular_user):
    client = as_user(regular_user)

    too_big = await client.get(FAV, params={"per_page": 21})
    zero = await client.get(FAV, params={"per_page": 0})
    bad_page = await client.get(FAV, params={"page": 0})

    assert too_big.status_code == 422
    assert zero.status_code == 422
    assert bad_page.status_code == 422
