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
    # ── users ─────────────────────────────────────────────────────────────────
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

    # ── departments ───────────────────────────────────────────────────────────
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('cost_center_prefix', sa.String(length=20), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ── employees ─────────────────────────────────────────────────────────────
    op.create_table(
        'employees',
        sa.Column('employee_id', sa.String(length=20), nullable=False),
        sa.Column('employee_name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=300), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('team', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('role', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('manager_id', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('cost_center', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('location', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('employment_type', sa.String(length=50), nullable=False, server_default='Full-time'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('sso_provider', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.PrimaryKeyConstraint('employee_id'),
    )

    # ── model_pricing ─────────────────────────────────────────────────────────
    op.create_table(
        'model_pricing',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('model_name', sa.String(length=200), nullable=False),
        sa.Column('tier', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('input_cost_per_1m_tokens', sa.Float(), nullable=False, server_default='0'),
        sa.Column('output_cost_per_1m_tokens', sa.Float(), nullable=False, server_default='0'),
        sa.Column('cached_input_cost_per_1m_tokens', sa.Float(), nullable=False, server_default='0'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name'),
    )

    # ── ai_licenses ───────────────────────────────────────────────────────────
    op.create_table(
        'ai_licenses',
        sa.Column('license_id', sa.String(length=30), nullable=False),
        sa.Column('employee_id', sa.String(length=20), nullable=False),
        sa.Column('tool_name', sa.String(length=200), nullable=False),
        sa.Column('plan_type', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('monthly_seat_cost', sa.Float(), nullable=False, server_default='0'),
        sa.Column('assigned_date', sa.Date(), nullable=True),
        sa.Column('last_active_date', sa.Date(), nullable=True),
        sa.Column('active_days_last_30', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('license_status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('department', sa.String(length=100), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('license_id'),
    )

    # ── ai_usage_events ───────────────────────────────────────────────────────
    op.create_table(
        'ai_usage_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='api_gateway'),
        sa.Column('employee_id', sa.String(length=20), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('team', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('internal_app', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('provider', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('model_name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('task_type', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status_code', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('request_allowed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expensive_model_simple_task', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id', name='uq_usage_event_trace_id'),
    )
    op.create_index(op.f('ix_ai_usage_events_timestamp'), 'ai_usage_events', ['timestamp'])
    op.create_index(op.f('ix_ai_usage_events_employee_id'), 'ai_usage_events', ['employee_id'])
    op.create_index(op.f('ix_ai_usage_events_department'), 'ai_usage_events', ['department'])
    op.create_index(op.f('ix_ai_usage_events_model_name'), 'ai_usage_events', ['model_name'])
    op.create_index(op.f('ix_ai_usage_events_trace_id'), 'ai_usage_events', ['trace_id'])

    # ── browser_events ────────────────────────────────────────────────────────
    op.create_table(
        'browser_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('employee_id', sa.String(length=20), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('session_id', sa.String(length=30), nullable=False, server_default=''),
        sa.Column('browser', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('domain', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('task_type', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('prompt_length_chars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('contains_pii', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pii_types_detected', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('policy_action', sa.String(length=30), nullable=False, server_default='allow'),
        sa.Column('shadow_ai_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_tool', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('copy_paste_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('file_upload_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index(op.f('ix_browser_events_timestamp'), 'browser_events', ['timestamp'])
    op.create_index(op.f('ix_browser_events_employee_id'), 'browser_events', ['employee_id'])
    op.create_index(op.f('ix_browser_events_event_id'), 'browser_events', ['event_id'])

    # ── kafka_events ──────────────────────────────────────────────────────────
    op.create_table(
        'kafka_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('employee_id', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('department', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('provider', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('model_name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('policy_result', sa.String(length=30), nullable=False, server_default='allowed'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id', name='uq_kafka_event_trace_id'),
    )
    op.create_index(op.f('ix_kafka_events_timestamp'), 'kafka_events', ['timestamp'])
    op.create_index(op.f('ix_kafka_events_trace_id'), 'kafka_events', ['trace_id'])

    # ── clickhouse_aggregates ─────────────────────────────────────────────────
    op.create_table(
        'clickhouse_aggregates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agg_id', sa.String(length=30), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('employee_id', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('department', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('provider', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('model_name', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_hit_rate', sa.Float(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agg_id'),
    )
    op.create_index(op.f('ix_clickhouse_aggregates_date'), 'clickhouse_aggregates', ['date'])

    # ── kubernetes_logs ───────────────────────────────────────────────────────
    op.create_table(
        'kubernetes_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('log_id', sa.String(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('cluster', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('namespace', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('pod_name', sa.String(length=100), nullable=False),
        sa.Column('gateway_version', sa.String(length=30), nullable=False, server_default=''),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rate', sa.Float(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p95_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cpu_usage_percent', sa.Float(), nullable=False, server_default='0'),
        sa.Column('memory_usage_mb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('restart_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='healthy'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('log_id'),
    )
    op.create_index(op.f('ix_kubernetes_logs_timestamp'), 'kubernetes_logs', ['timestamp'])
    op.create_index(op.f('ix_kubernetes_logs_pod_name'), 'kubernetes_logs', ['pod_name'])

    # ── integration_sync_runs ─────────────────────────────────────────────────
    op.create_table(
        'integration_sync_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='csv'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_ingested', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rows_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('validation_warnings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='running'),
        sa.Column('error_message', sa.Text(), nullable=False, server_default=''),
        sa.Column('schema_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('triggered_by', sa.String(length=300), nullable=False, server_default='system'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_integration_sync_runs_source_name'), 'integration_sync_runs', ['source_name'])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=200), nullable=False, server_default='system'),
        sa.Column('actor_user_id', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('actor_email', sa.String(length=300), nullable=False, server_default=''),
        sa.Column('actor_role', sa.String(length=30), nullable=False, server_default=''),
        sa.Column('resource_type', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('resource_id', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('details', sa.Text(), nullable=False, server_default=''),
        sa.Column('ip_address', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('user_agent', sa.String(length=500), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'])

    # ── recommendations ───────────────────────────────────────────────────────
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('signature_hash', sa.String(length=64), nullable=False),
        sa.Column('recommendation_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('department', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('employee_id', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('reasoning', sa.Text(), nullable=False, server_default=''),
        sa.Column('estimated_monthly_savings', sa.Float(), nullable=False, server_default='0'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('requires_human_review', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('reviewed_by', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('investigation_notes', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signature_hash', name='uq_recommendation_signature'),
    )
    op.create_index('ix_recommendations_signature_hash', 'recommendations', ['signature_hash'])


def downgrade() -> None:
    op.drop_table('recommendations')
    op.drop_table('audit_logs')
    op.drop_table('integration_sync_runs')
    op.drop_table('kubernetes_logs')
    op.drop_table('clickhouse_aggregates')
    op.drop_table('kafka_events')
    op.drop_table('browser_events')
    op.drop_table('ai_usage_events')
    op.drop_table('ai_licenses')
    op.drop_table('model_pricing')
    op.drop_table('employees')
    op.drop_table('departments')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
