"""Add User, Profile, and EvaluationRecord tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("role", sa.String(), server_default="learner"),
        sa.Column("auth_provider", sa.String(), server_default="local"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("data", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)

    op.create_table(
        "evaluation_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario_id", sa.String(), nullable=False),
        sa.Column("response_text", sa.String()),
        sa.Column("model_used", sa.String()),
        sa.Column("raw_result", sa.JSON()),
        sa.Column("parsed_result", sa.JSON()),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("verification_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluation_records_user_id", "evaluation_records", ["user_id"])
    op.create_index("ix_evaluation_records_scenario_id", "evaluation_records", ["scenario_id"])


def downgrade():
    op.drop_table("evaluation_records")
    op.drop_table("profiles")
    op.drop_table("users")
