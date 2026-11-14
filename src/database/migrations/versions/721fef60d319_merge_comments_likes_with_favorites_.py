"""merge comments-likes with favorites-ratings

Revision ID: 721fef60d319
Revises: e1d0c5a5173b, c3d8f2a71b64
Create Date: 2026-11-14 16:52:07.118385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '721fef60d319'
down_revision: Union[str, Sequence[str], None] = ('e1d0c5a5173b', 'c3d8f2a71b64')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
