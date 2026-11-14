"""merge heads

Revision ID: b7c4e1a09d3f
Revises: 672d810ca226, 69e2f43927aa
"""
from typing import Sequence, Union

revision: str = "b7c4e1a09d3f"
down_revision: Union[str, Sequence[str], None] = ("672d810ca226", "69e2f43927aa")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass