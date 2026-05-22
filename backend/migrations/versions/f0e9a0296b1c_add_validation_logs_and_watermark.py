"""add_validation_logs_and_watermark

Revision ID: f0e9a0296b1c
Revises: 4d20fec4e57d
Create Date: 2026-05-22 02:48:25.820278

Adds:
  - ingestion_validation_logs table (row-level schema drift records)
  - integration_sync_runs.watermark_since column (incremental sync cutoff)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'f0e9a0296b1c'
down_revision: Union[str, Sequence[str], None] = '4d20fec4e57d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(name)


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _table_exists("ingestion_validation_logs"):
        op.create_table(
            'ingestion_validation_logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('run_id', sa.Integer(), nullable=True),
            sa.Column('connector_name', sa.String(length=100), nullable=False),
            sa.Column('row_number', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('field_name', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('error_type', sa.String(length=50), nullable=False, server_default=''),
            sa.Column('raw_value', sa.Text(), nullable=False, server_default=''),
            sa.Column('error_message', sa.Text(), nullable=False, server_default=''),
            sa.ForeignKeyConstraint(['run_id'], ['integration_sync_runs.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_ingestion_validation_logs_created_at', 'ingestion_validation_logs', ['created_at'])
        op.create_index('ix_ingestion_validation_logs_connector_name', 'ingestion_validation_logs', ['connector_name'])
        op.create_index('ix_ingestion_validation_logs_run_id', 'ingestion_validation_logs', ['run_id'])

    if not _column_exists("integration_sync_runs", "watermark_since"):
        op.add_column(
            'integration_sync_runs',
            sa.Column('watermark_since', sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("integration_sync_runs", "watermark_since"):
        op.drop_column('integration_sync_runs', 'watermark_since')
    if _table_exists("ingestion_validation_logs"):
        op.drop_index('ix_ingestion_validation_logs_run_id', table_name='ingestion_validation_logs')
        op.drop_index('ix_ingestion_validation_logs_connector_name', table_name='ingestion_validation_logs')
        op.drop_index('ix_ingestion_validation_logs_created_at', table_name='ingestion_validation_logs')
        op.drop_table('ingestion_validation_logs')
