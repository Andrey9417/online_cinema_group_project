API = "/api/v1"
MOVIES = f"{API}/movies"
COMMENTS = f"{API}/comments"


async def _make_comment(client, movie_id, text="hi"):
    resp = await client.post(
        f"{MOVIES}/{movie_id}/comments/", json={"text": text}
    )
    return resp.json()


# ---------- movie likes ----------
async def test_like_movie(as_user, regular_user, make_movie):
    movie = await make_movie()
    resp = await as_user(regular_user).post(
        f"{MOVIES}/{movie['id']}/like/", json={"is_like": True}
    )
    assert resp.status_code == 200
    assert resp.json()["is_like"] is True


async def test_movie_like_counts(as_user, regular_user, make_movie, client):
    movie = await make_movie()
    await as_user(regular_user).post(
        f"{MOVIES}/{movie['id']}/like/", json={"is_like": True}
    )
    resp = await client.get(f"{MOVIES}/{movie['id']}/likes/")
    assert resp.status_code == 200
    assert resp.json() == {"likes": 1, "dislikes": 0}


async def test_movie_reaction_updates_not_duplicates(
        as_user, regular_user, make_movie, client
):
    movie = await make_movie()
    author = as_user(regular_user)
    await author.post(f"{MOVIES}/{movie['id']}/like/", json={"is_like": True})
    await author.post(f"{MOVIES}/{movie['id']}/like/", json={"is_like": False})
    resp = await client.get(f"{MOVIES}/{movie['id']}/likes/")
    assert resp.json() == {"likes": 0, "dislikes": 1}


async def test_delete_movie_like(as_user, regular_user, make_movie, client):
    movie = await make_movie()
    author = as_user(regular_user)
    await author.post(f"{MOVIES}/{movie['id']}/like/", json={"is_like": True})
    resp = await author.delete(f"{MOVIES}/{movie['id']}/like/")
    assert resp.status_code == 204
    counts = await client.get(f"{MOVIES}/{movie['id']}/likes/")
    assert counts.json() == {"likes": 0, "dislikes": 0}


async def test_like_missing_movie_404(as_user, regular_user, catalog):
    resp = await as_user(regular_user).post(
        f"{MOVIES}/999999/like/", json={"is_like": True}
    )
    assert resp.status_code == 404


# ---------- comment reactions ----------
async def test_react_to_comment(as_user, regular_user, make_movie):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = await _make_comment(author, movie["id"])
    resp = await author.post(
        f"{COMMENTS}/{comment['id']}/reactions/", json={"is_like": True}
    )
    assert resp.status_code == 201
    assert resp.json()["is_like"] is True


async def test_comment_reaction_counts(
        as_user, regular_user, make_movie, client
):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = await _make_comment(author, movie["id"])
    await author.post(
        f"{COMMENTS}/{comment['id']}/reactions/", json={"is_like": True}
    )
    resp = await client.get(f"{COMMENTS}/{comment['id']}/reactions/")
    assert resp.status_code == 200
    assert resp.json() == {"likes": 1, "dislikes": 0}


async def test_comment_reaction_updates(
        as_user, regular_user, make_movie, client
):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = await _make_comment(author, movie["id"])
    await author.post(
        f"{COMMENTS}/{comment['id']}/reactions/", json={"is_like": True}
    )
    await author.post(
        f"{COMMENTS}/{comment['id']}/reactions/", json={"is_like": False}
    )
    resp = await client.get(f"{COMMENTS}/{comment['id']}/reactions/")
    assert resp.json() == {"likes": 0, "dislikes": 1}


async def test_delete_comment_reaction(
        as_user, regular_user, make_movie, client
):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = await _make_comment(author, movie["id"])
    await author.post(
        f"{COMMENTS}/{comment['id']}/reactions/", json={"is_like": True}
    )
    resp = await author.delete(f"{COMMENTS}/{comment['id']}/reactions/")
    assert resp.status_code == 204
    counts = await client.get(f"{COMMENTS}/{comment['id']}/reactions/")
    assert counts.json() == {"likes": 0, "dislikes": 0}


async def test_react_to_missing_comment_404(as_user, regular_user, catalog):
    resp = await as_user(regular_user).post(
        f"{COMMENTS}/999999/reactions/", json={"is_like": True}
    )
    assert resp.status_code == 404
