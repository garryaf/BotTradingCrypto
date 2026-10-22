"""005_user_roles

Revision ID: 005_user_roles
Revises: 004_users_and_account_scoping
Create Date: 2026-10-21 00:00:00

Adds a role column ("user" | "admin") to users. Admin manages the user list;
a plain user only ever sees/trades their own account (unchanged).
"""
from alembic import op
import sqlalchemy as sa

revision = "005_user_roles"
down_revision = "004_users_and_account_scoping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="user"))


def downgrade() -> None:
    op.drop_column("users", "role")
