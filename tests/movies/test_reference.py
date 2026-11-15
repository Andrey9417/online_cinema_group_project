API = "/api/v1"


async def test_list_genres_is_public(client):
    resp = await client.get(f"{API}/genres/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_create_genre_as_moderator(as_user, moderator):
    resp = await as_user(moderator).post(f"{API}/genres/", json={"name": "Horror"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Horror"


async def test_create_genre_as_regular_user_forbidden(as_user, regular_user):
    resp = await as_user(regular_user).post(
        f"{API}/genres/", json={"name": "Horror"}
    )
    assert resp.status_code == 403


async def test_create_genre_unauthenticated(client):
    resp = await client.post(f"{API}/genres/", json={"name": "Horror"})
    assert resp.status_code in (401, 403)


async def test_create_duplicate_genre_returns_409(as_user, moderator):
    client = as_user(moderator)
    await client.post(f"{API}/genres/", json={"name": "Horror"})
    resp = await client.post(f"{API}/genres/", json={"name": "Horror"})
    assert resp.status_code == 409


async def test_update_genre(as_user, moderator):
    client = as_user(moderator)
    created = (
        await client.post(f"{API}/genres/", json={"name": "Horror"})
    ).json()
    resp = await client.put(
        f"{API}/genres/{created['id']}/", json={"name": "Thriller"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Thriller"


async def test_update_missing_genre_returns_404(as_user, moderator):
    resp = await as_user(moderator).put(
        f"{API}/genres/999999/", json={"name": "X"}
    )
    assert resp.status_code == 404


async def test_delete_genre(as_user, moderator):
    client = as_user(moderator)
    created = (
        await client.post(f"{API}/genres/", json={"name": "Horror"})
    ).json()
    resp = await client.delete(f"{API}/genres/{created['id']}/")
    assert resp.status_code == 204
    again = await client.delete(f"{API}/genres/{created['id']}/")
    assert again.status_code == 404


async def test_create_star_and_director(as_user, moderator):
    client = as_user(moderator)
    star = await client.post(f"{API}/stars/", json={"name": "Carrie-Anne Moss"})
    director = await client.post(
        f"{API}/directors/", json={"name": "Lana Wachowski"}
    )
    assert star.status_code == 201
    assert director.status_code == 201
