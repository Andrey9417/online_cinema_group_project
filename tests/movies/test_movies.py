API = "/api/v1"
MOVIES = f"{API}/movies"


async def test_movie_detail_returns_movie(client, make_movie):
    movie = await make_movie(name="Inception")
    resp = await client.get(f"{MOVIES}/{movie['id']}/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Inception"


async def test_movie_detail_missing_returns_404(client, catalog):
    resp = await client.get(f"{MOVIES}/999999/")
    assert resp.status_code == 404


async def test_create_movie_requires_moderator(
        as_user, regular_user, movie_payload
):
    resp = await as_user(regular_user).post(f"{MOVIES}/", json=movie_payload)
    assert resp.status_code == 403


async def test_create_movie_as_moderator(as_user, moderator, movie_payload):
    resp = await as_user(moderator).post(f"{MOVIES}/", json=movie_payload)
    assert resp.status_code == 201
    assert resp.json()["name"] == movie_payload["name"]


async def test_update_movie(as_user, moderator, make_movie):
    movie = await make_movie()
    resp = await as_user(moderator).put(
        f"{MOVIES}/{movie['id']}/", json={"name": "Renamed"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


async def test_list_pagination(client, make_movie):
    for i in range(3):
        await make_movie(name=f"Movie {i}", year=2000 + i)
    resp = await client.get(f"{MOVIES}/", params={"page": 1, "per_page": 2})
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["movies"]) == 2
    assert body["total_items"] == 3
    assert body["total_pages"] == 2
    assert body["prev_page"] is None
    assert body["next_page"] is not None


async def test_filter_by_year(client, make_movie):
    await make_movie(name="Old", year=1990)
    await make_movie(name="New", year=2020)
    resp = await client.get(f"{MOVIES}/", params={"year": 2020})
    names = [m["name"] for m in resp.json()["movies"]]
    assert names == ["New"]


async def test_filter_by_min_imdb(client, make_movie):
    await make_movie(name="Low", imdb=5.0)
    await make_movie(name="High", imdb=9.0)
    resp = await client.get(f"{MOVIES}/", params={"min_imdb": 8})
    names = [m["name"] for m in resp.json()["movies"]]
    assert names == ["High"]


async def test_search_by_title(client, make_movie):
    await make_movie(name="Interstellar")
    await make_movie(name="Tenet")
    resp = await client.get(f"{MOVIES}/", params={"search": "stellar"})
    names = [m["name"] for m in resp.json()["movies"]]
    assert names == ["Interstellar"]


async def test_search_by_star(client, make_movie):
    await make_movie(name="John Wick")  # default star is Keanu Reeves
    resp = await client.get(f"{MOVIES}/", params={"search": "Keanu"})
    names = [m["name"] for m in resp.json()["movies"]]
    assert "John Wick" in names


async def test_sort_by_year_desc(client, make_movie):
    await make_movie(name="A", year=1990)
    await make_movie(name="B", year=2020)
    resp = await client.get(
        f"{MOVIES}/", params={"sort_by": "year", "order": "desc"}
    )
    names = [m["name"] for m in resp.json()["movies"]]
    assert names == ["B", "A"]


async def test_sort_by_year_asc(client, make_movie):
    await make_movie(name="A", year=1990)
    await make_movie(name="B", year=2020)
    resp = await client.get(
        f"{MOVIES}/", params={"sort_by": "year", "order": "asc"}
    )
    names = [m["name"] for m in resp.json()["movies"]]
    assert names == ["A", "B"]


async def test_create_movie_invalid_year_returns_422(
        as_user, moderator, movie_payload
):
    resp = await as_user(moderator).post(
        f"{MOVIES}/", json={**movie_payload, "year": 1700}
    )
    assert resp.status_code == 422


async def test_create_movie_invalid_imdb_returns_422(
        as_user, moderator, movie_payload
):
    resp = await as_user(moderator).post(
        f"{MOVIES}/", json={**movie_payload, "imdb": 15}
    )
    assert resp.status_code == 422


async def test_update_movie_invalid_imdb_returns_422(
        as_user, moderator, make_movie
):
    movie = await make_movie()
    resp = await as_user(moderator).put(
        f"{MOVIES}/{movie['id']}/", json={"imdb": -1}
    )
    assert resp.status_code == 422
