"""Drop vestigial guac_connection_id from environments table (ARCH-15).

The column was used for static pre-configured Guacamole connections before
SEC-02 introduced ephemeral per-session connections. It is no longer written
or read. LabSession.guac_connection_id (dynamic, per-session) is untouched.

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("environments")]
    if "guac_connection_id" in columns:
        op.drop_column("environments", "guac_connection_id")


def downgrade():
    op.add_column("environments", sa.Column("guac_connection_id", sa.String(), nullable=True))
