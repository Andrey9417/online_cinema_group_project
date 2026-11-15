API = "/api/v1"
MOVIES = f"{API}/movies"
COMMENTS = f"{API}/comments"


async def test_add_comment(as_user, regular_user, make_movie):
    movie = await make_movie()
    resp = await as_user(regular_user).post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "Great movie!"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["text"] == "Great movie!"
    assert body["movie_id"] == movie["id"]
    assert body["parent_id"] is None


async def test_add_comment_to_missing_movie_404(as_user, regular_user, catalog):
    resp = await as_user(regular_user).post(
        f"{MOVIES}/999999/comments/", json={"text": "x"}
    )
    assert resp.status_code == 404


async def test_list_comments(as_user, regular_user, make_movie, client):
    movie = await make_movie()
    author = as_user(regular_user)
    await author.post(f"{MOVIES}/{movie['id']}/comments/", json={"text": "first"})
    await author.post(f"{MOVIES}/{movie['id']}/comments/", json={"text": "second"})
    resp = await client.get(f"{MOVIES}/{movie['id']}/comments/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_reply_to_comment(as_user, regular_user, make_movie):
    movie = await make_movie()
    author = as_user(regular_user)
    parent = (await author.post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "parent"}
    )).json()
    resp = await author.post(
        f"{COMMENTS}/{parent['id']}/reply/", json={"text": "child"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["parent_id"] == parent["id"]
    assert body["movie_id"] == movie["id"]


async def test_reply_to_missing_comment_404(as_user, regular_user, catalog):
    resp = await as_user(regular_user).post(
        f"{COMMENTS}/999999/reply/", json={"text": "x"}
    )
    assert resp.status_code == 404


async def test_edit_own_comment(as_user, regular_user, make_movie):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = (await author.post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "old"}
    )).json()
    resp = await author.put(f"{COMMENTS}/{comment['id']}/", json={"text": "new"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "new"


async def test_edit_others_comment_forbidden(
        as_user, regular_user, make_user, make_movie
):
    movie = await make_movie()
    comment = (await as_user(regular_user).post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "mine"}
    )).json()
    other = await make_user(email="other@example.com")
    resp = await as_user(other).put(
        f"{COMMENTS}/{comment['id']}/", json={"text": "hacked"}
    )
    assert resp.status_code == 403


async def test_delete_own_comment(as_user, regular_user, make_movie):
    movie = await make_movie()
    author = as_user(regular_user)
    comment = (await author.post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "bye"}
    )).json()
    resp = await author.delete(f"{COMMENTS}/{comment['id']}/")
    assert resp.status_code == 204


async def test_delete_others_comment_forbidden(
        as_user, regular_user, make_user, make_movie
):
    movie = await make_movie()
    comment = (await as_user(regular_user).post(
        f"{MOVIES}/{movie['id']}/comments/", json={"text": "mine"}
    )).json()
    other = await make_user(email="other@example.com")
    resp = await as_user(other).delete(f"{COMMENTS}/{comment['id']}/")
    assert resp.status_code == 403
