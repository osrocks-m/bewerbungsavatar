"""Add bewerbung_id and client_id to conversations

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("bewerbung_id", sa.String(100), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "conversations",
        sa.Column("client_id", sa.String(36), nullable=False, server_default="unknown"),
    )
    op.create_index(
        "ix_conversations_bewerbung_client",
        "conversations",
        ["bewerbung_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_bewerbung_client", table_name="conversations")
    op.drop_column("conversations", "client_id")
    op.drop_column("conversations", "bewerbung_id")
