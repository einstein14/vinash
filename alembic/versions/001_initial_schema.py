"""Initial schema with anonymous users.

Revision ID: 001
Revises:
Create Date: 2026-09-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anonymous_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "thoughts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("anonymous_user_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revisit_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["anonymous_user_id"], ["anonymous_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_thoughts_user_status_created",
        "thoughts",
        ["anonymous_user_id", "status", "created_at"],
    )
    op.create_index(
        "idx_thoughts_user_revisit",
        "thoughts",
        ["anonymous_user_id", "revisit_at"],
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thought_id", sa.Integer(), nullable=False),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["thought_id"], ["thoughts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thought_id", name="uq_actions_thought_id"),
    )


def downgrade() -> None:
    op.drop_table("actions")
    op.drop_index("idx_thoughts_user_revisit", table_name="thoughts")
    op.drop_index("idx_thoughts_user_status_created", table_name="thoughts")
    op.drop_table("thoughts")
    op.drop_table("anonymous_users")
