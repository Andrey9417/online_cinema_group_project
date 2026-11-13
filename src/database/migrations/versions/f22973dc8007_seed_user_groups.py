"""seed user groups

Revision ID: f22973dc8007
Revises: 45d97e95c320
Create Date: 2026-11-12 17:28:46.575100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f22973dc8007'
down_revision: Union[str, Sequence[str], None] = '45d97e95c320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO user_groups (name)
        VALUES ('USER'), ('MODERATOR'), ('ADMIN')
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM user_groups WHERE name IN ('USER', 'MODERATOR', 'ADMIN')"
    )
