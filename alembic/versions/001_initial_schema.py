"""Initial schema - conversations, evaluations, improvement_suggestions

Revision ID: 001
Revises:
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.String(100), nullable=False),
        sa.Column("agent_version", sa.String(50), nullable=False),
        sa.Column("turns", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_conversation_id", "conversations", ["conversation_id"], unique=True)
    op.create_index("ix_conversations_agent_version", "conversations", ["agent_version"])

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", sa.String(100), nullable=False),
        sa.Column("conversation_id", sa.String(100), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("tool_evaluation", sa.JSON(), nullable=True),
        sa.Column("issues_detected", sa.JSON(), nullable=True),
        sa.Column("improvement_suggestions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.conversation_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluations_evaluation_id", "evaluations", ["evaluation_id"], unique=True)
    op.create_index("ix_evaluations_conversation_id", "evaluations", ["conversation_id"])

    op.create_table(
        "improvement_suggestions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suggestion_type", sa.String(50), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_improvement_suggestions_suggestion_type", "improvement_suggestions", ["suggestion_type"])


def downgrade() -> None:
    op.drop_table("improvement_suggestions")
    op.drop_table("evaluations")
    op.drop_table("conversations")
