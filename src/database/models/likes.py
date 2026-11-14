from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class MovieLike(Base):
    __tablename__ = "movie_likes"

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE")
    )
    is_like: Mapped[bool]
