from decimal import Decimal

from database.models.orders import Order, OrderItem, OrderStatusEnum

API = "/api/v1"
MOVIES = f"{API}/movies"


async def _add_order(db_session, user_id, movie_id, status):
    order = Order(
        user_id=user_id,
        status=status,
        total_amount=Decimal("9.99"),
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order.id,
            movie_id=movie_id,
            price_at_order=Decimal("9.99"),
        )
    )
    await db_session.commit()


async def test_delete_movie_as_moderator(as_user, moderator, make_movie):
    movie = await make_movie()
    resp = await as_user(moderator).delete(f"{MOVIES}/{movie['id']}/")
    assert resp.status_code == 204


async def test_delete_movie_forbidden_for_regular(
        as_user, regular_user, make_movie
):
    movie = await make_movie()
    resp = await as_user(regular_user).delete(f"{MOVIES}/{movie['id']}/")
    assert resp.status_code == 403


async def test_delete_missing_movie_returns_404(as_user, moderator, catalog):
    resp = await as_user(moderator).delete(f"{MOVIES}/999999/")
    assert resp.status_code == 404


async def test_delete_purchased_movie_returns_409(
        as_user, moderator, regular_user, make_movie, db_session
):
    movie = await make_movie()
    await _add_order(
        db_session, regular_user.id, movie["id"], OrderStatusEnum.PAID
    )
    resp = await as_user(moderator).delete(f"{MOVIES}/{movie['id']}/")
    assert resp.status_code == 409
