"""add_ocr_correction_fields

Revision ID: fe6acbbdd10a
Revises: 3856cf9ae086
Create Date: 2025-06-23 16:55:29.982964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe6acbbdd10a'
down_revision: Union[str, None] = '3856cf9ae086'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OCR correction fields to drawings table
    op.add_column('drawings', sa.Column('ocr_merged_result_key', sa.String(), nullable=True))
    op.add_column('drawings', sa.Column('ocr_corrected_result_key', sa.String(), nullable=True))
    op.add_column('drawings', sa.Column('ocr_correction_summary', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove OCR correction fields from drawings table
    op.drop_column('drawings', 'ocr_correction_summary')
    op.drop_column('drawings', 'ocr_corrected_result_key')
    op.drop_column('drawings', 'ocr_merged_result_key')
