"""Add guac_session_username and guac_session_password to sessions table (SEC-07).

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("guac_session_username", sa.String(), nullable=True))
    op.add_column("sessions", sa.Column("guac_session_password", sa.String(), nullable=True))


def downgrade():
    op.drop_column("sessions", "guac_session_password")
    op.drop_column("sessions", "guac_session_username")
