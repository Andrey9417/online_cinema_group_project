"""merge heads

Revision ID: c3d8f2a71b64
Revises: 5a1984bd45fe, e0d6ca893df9
"""
from typing import Sequence, Union

revision: str = "c3d8f2a71b64"
down_revision: Union[str, Sequence[str], None] = ("5a1984bd45fe", "e0d6ca893df9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
