"""002_add_scheduled_job_executions

Revision ID: 002_job_executions
Revises: 001_initial_schema
Create Date: 2026-10-12 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_job_executions"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Scheduled Job Executions Table
    op.create_table(
        "scheduled_job_executions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column("execution_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("node_id", sa.String(128), nullable=False),
        sa.Column("execution_status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_name", "execution_date", name="uq_job_name_execution_date"),
    )
    op.create_index("idx_job_exec_status", "scheduled_job_executions", ["job_name", "execution_status"])
    op.create_index("idx_exec_date", "scheduled_job_executions", ["execution_date"])


def downgrade() -> None:
    op.drop_index("idx_exec_date", table_name="scheduled_job_executions")
    op.drop_index("idx_job_exec_status", table_name="scheduled_job_executions")
    op.drop_table("scheduled_job_executions")
