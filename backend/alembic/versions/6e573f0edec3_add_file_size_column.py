"""add_file_size_column

Revision ID: 6e573f0edec3
Revises: 4d23052f2c95
Create Date: 2025-06-02 00:50:13.215773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e573f0edec3'
down_revision: Union[str, None] = '4d23052f2c95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加file_size列到drawings表
    op.add_column('drawings', sa.Column('file_size', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    # 删除file_size列
    op.drop_column('drawings', 'file_size')
