import asyncio
from decimal import Decimal

from sqlalchemy import insert, select

from database.models import UserGroupEnum, Movie, Certification, Genre, Director, Star, UserGroup, User, Comment, \
    MovieLike, MovieRating, CommentLike, FavoriteMoviesTable
from database.session import AsyncSessionLocal

DEMO_PASSWORD = "Demo12345!"  # demo only

CERTIFICATIONS = ["PG", "PG-13", "R"]
GENRES = ["Action", "Drama", "Sci-Fi", "Comedy", "Animation"]
DIRECTORS = ["Director One", "Director Two", "Director Three"]
STARS = ["Actor A", "Actor B", "Actor C", "Actor D"]

MOVIES = [
    dict(name="Sample Movie 1", year=2020, time=120, imdb=8.1, votes=250000,
         meta_score=75.0, gross=150000000.0, price="9.99", cert="PG-13",
         genres=["Action", "Sci-Fi"], directors=["Director One"], stars=["Actor A", "Actor B"],
         description="A sample action movie for the demo."),
    dict(name="Sample Movie 2", year=2018, time=105, imdb=7.4, votes=90000,
         meta_score=None, gross=None, price="7.99", cert="R",
         genres=["Drama"], directors=["Director Two"], stars=["Actor C"],
         description="A sample drama for the demo."),
    dict(name="Sample Movie 3", year=2022, time=95, imdb=7.9, votes=120000,
         meta_score=68.0, gross=80000000.0, price="5.99", cert="PG",
         genres=["Animation", "Comedy"], directors=["Director Three"], stars=["Actor D", "Actor A"],
         description="A sample animated comedy for the demo."),
]

USERS = [
    ("admin@demo.local", UserGroupEnum.ADMIN),
    ("moderator@demo.local", UserGroupEnum.MODERATOR),
    ("user@demo.local", UserGroupEnum.USER),
]


async def seed(session) -> None:
    if (await session.execute(select(Movie.id).limit(1))).first():
        print("Movies already exist, skipping.")
        return

    certs = {n: Certification(name=n) for n in CERTIFICATIONS}
    genres = {n: Genre(name=n) for n in GENRES}
    directors = {n: Director(name=n) for n in DIRECTORS}
    stars = {n: Star(name=n) for n in STARS}

    movies = [
        Movie(
            name=m["name"], year=m["year"], time=m["time"], imdb=m["imdb"],
            votes=m["votes"], meta_score=m["meta_score"], gross=m["gross"],
            description=m["description"], price=Decimal(m["price"]),
            certification=certs[m["cert"]],
            genres=[genres[g] for g in m["genres"]],
            directors=[directors[d] for d in m["directors"]],
            stars=[stars[s] for s in m["stars"]],
        )
        for m in MOVIES
    ]
    session.add_all(movies)

    groups = {g.name: g.id for g in (await session.execute(select(UserGroup))).scalars()}
    users = []
    for email, group in USERS:
        user = User.cool_create(email, DEMO_PASSWORD, groups[group])
        user.is_active = True  # skip the email activation flow
        users.append(user)
    session.add_all(users)
    await session.flush()  # assigns ids

    _, moderator, user = users
    comment = Comment(user_id=user.id, movie_id=movies[0].id, text="Great movie!")
    session.add(comment)
    await session.flush()
    session.add_all([
        Comment(user_id=moderator.id, movie_id=movies[0].id, parent_id=comment.id, text="Agreed."),
        MovieLike(user_id=user.id, movie_id=movies[0].id, is_like=True),
        MovieRating(user_id=user.id, movie_id=movies[0].id, rating=9),
        CommentLike(user_id=moderator.id, comment_id=comment.id, is_like=True),
    ])
    await session.execute(
        insert(FavoriteMoviesTable).values(user_id=user.id, movie_id=movies[1].id)
    )
    await session.commit()
    print("Seeding completed.")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
