"""Add verification_results JSON column to sessions table (ARCH-17).

Stores the output of POST /lab/verify so the AI evaluator can include
automated lab check results as context when assessing the learner's response.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("verification_results", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("sessions", "verification_results")
