"""baseline_with_auth_and_upsert_constraints

Revision ID: 4d20fec4e57d
Revises:
Create Date: 2026-05-22 01:09:17.587277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4d20fec4e57d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users table (new) ─────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=300), nullable=False),
        sa.Column('hashed_password', sa.String(length=300), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('role', sa.String(length=30), nullable=False, server_default='analyst'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # ── ai_usage_events: add unique constraint on trace_id ───────────────────
    op.create_unique_constraint('uq_usage_event_trace_id', 'ai_usage_events', ['trace_id'])

    # ── kafka_events: add unique constraint on trace_id ──────────────────────
    op.create_unique_constraint('uq_kafka_event_trace_id', 'kafka_events', ['trace_id'])

    # ── audit_logs: add actor attribution + request context columns ──────────
    # server_default='' so existing rows are populated safely
    op.add_column('audit_logs', sa.Column('actor_user_id', sa.String(50), nullable=False, server_default=''))
    op.add_column('audit_logs', sa.Column('actor_email', sa.String(300), nullable=False, server_default=''))
    op.add_column('audit_logs', sa.Column('actor_role', sa.String(30), nullable=False, server_default=''))
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(50), nullable=False, server_default=''))
    op.add_column('audit_logs', sa.Column('user_agent', sa.String(500), nullable=False, server_default=''))

    # ── integration_sync_runs: add observability columns ─────────────────────
    op.add_column('integration_sync_runs', sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('integration_sync_runs', sa.Column('rows_updated', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('integration_sync_runs', sa.Column('rows_skipped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('integration_sync_runs', sa.Column('validation_warnings_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('integration_sync_runs', sa.Column('triggered_by', sa.String(300), nullable=False, server_default='system'))

    # ── recommendations: lifecycle + deduplication columns ───────────────────
    op.add_column('recommendations', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    op.add_column('recommendations', sa.Column('resolved_at', sa.DateTime(), nullable=True))
    op.add_column('recommendations', sa.Column('investigation_notes', sa.Text(), nullable=False, server_default=''))

    # signature_hash: add nullable first so we can backfill, then constrain
    op.add_column('recommendations', sa.Column('signature_hash', sa.String(64), nullable=True))
    # Backfill existing rows with a unique hash derived from their PK
    op.execute("UPDATE recommendations SET signature_hash = md5('legacy_' || id::text) WHERE signature_hash IS NULL")
    op.alter_column('recommendations', 'signature_hash', nullable=False)
    op.create_index('ix_recommendations_signature_hash', 'recommendations', ['signature_hash'], unique=False)
    op.create_unique_constraint('uq_recommendation_signature', 'recommendations', ['signature_hash'])


def downgrade() -> None:
    op.drop_constraint('uq_recommendation_signature', 'recommendations', type_='unique')
    op.drop_index('ix_recommendations_signature_hash', table_name='recommendations')
    op.drop_column('recommendations', 'signature_hash')
    op.drop_column('recommendations', 'investigation_notes')
    op.drop_column('recommendations', 'resolved_at')
    op.drop_column('recommendations', 'updated_at')
    op.drop_column('integration_sync_runs', 'triggered_by')
    op.drop_column('integration_sync_runs', 'validation_warnings_count')
    op.drop_column('integration_sync_runs', 'rows_skipped')
    op.drop_column('integration_sync_runs', 'rows_updated')
    op.drop_column('integration_sync_runs', 'duration_ms')
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'actor_role')
    op.drop_column('audit_logs', 'actor_email')
    op.drop_column('audit_logs', 'actor_user_id')
    op.drop_constraint('uq_kafka_event_trace_id', 'kafka_events', type_='unique')
    op.drop_constraint('uq_usage_event_trace_id', 'ai_usage_events', type_='unique')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
