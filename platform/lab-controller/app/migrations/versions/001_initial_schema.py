"""Initial schema — baseline from existing SQLite tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "environments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("vms", sa.JSON()),
        sa.Column("guac_connection_id", sa.String(), nullable=True),
        sa.Column("guac_target_vm", sa.String(), nullable=True),
        sa.Column("guac_protocol", sa.String(), nullable=True),
        sa.Column("capabilities", sa.JSON()),
        sa.Column("status", sa.String(), server_default="available"),
        sa.Column("provision_step", sa.String(), nullable=True),
        sa.Column("provision_step_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("faulted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fault_retry_count", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "sessions",
        sa.Column("session_token", sa.String(), primary_key=True),
        sa.Column("environment_id", sa.String(), sa.ForeignKey("environments.id")),
        sa.Column("user_id", sa.String()),
        sa.Column("scenario_id", sa.String()),
        sa.Column("guac_connection_id", sa.String(), nullable=True),
        sa.Column("suspect", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "heartbeats",
        sa.Column("job_name", sa.String(), primary_key=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table("heartbeats")
    op.drop_table("sessions")
    op.drop_table("environments")
