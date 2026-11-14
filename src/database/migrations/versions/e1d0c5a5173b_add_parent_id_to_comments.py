"""Add parent_id to comments

Revision ID: e1d0c5a5173b
Revises: 5a1984bd45fe
Create Date: 2026-11-14 15:17:17.149861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1d0c5a5173b'
down_revision: Union[str, Sequence[str], None] = '5a1984bd45fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_comments_parent_id',
        'comments', 'comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_comments_parent_id', 'comments', type_='foreignkey'
    )
    op.drop_column('comments', 'parent_id')
