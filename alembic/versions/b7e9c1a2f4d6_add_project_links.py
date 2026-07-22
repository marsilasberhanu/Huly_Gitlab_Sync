"""add project links and tenant issue mappings

Revision ID: b7e9c1a2f4d6
Revises: a4cc0e3b36f8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e9c1a2f4d6"
down_revision: Union[str, None] = "a4cc0e3b36f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_links",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "gitlab_project_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "gitlab_project_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "huly_project_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "huly_project_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "webhook_secret_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "gitlab_project_id",
            "huly_project_id",
            name="uq_project_link_user_projects",
        ),
    )

    op.create_index(
        "ix_project_links_id",
        "project_links",
        ["id"],
    )
    op.create_index(
        "ix_project_links_user_id",
        "project_links",
        ["user_id"],
    )
    op.create_index(
        "ix_project_links_gitlab_project_id",
        "project_links",
        ["gitlab_project_id"],
    )
    op.create_index(
        "ix_project_links_huly_project_id",
        "project_links",
        ["huly_project_id"],
    )

    op.add_column(
        "issue_mapping",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "issue_mapping",
        sa.Column(
            "project_link_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_issue_mapping_user_id",
        "issue_mapping",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_issue_mapping_project_link_id",
        "issue_mapping",
        "project_links",
        ["project_link_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_issue_mapping_user_id",
        "issue_mapping",
        ["user_id"],
    )
    op.create_index(
        "ix_issue_mapping_project_link_id",
        "issue_mapping",
        ["project_link_id"],
    )

    op.drop_constraint(
        "uq_gitlab_issue_mapping",
        "issue_mapping",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_project_link_gitlab_issue",
        "issue_mapping",
        ["project_link_id", "gitlab_issue_id"],
    )
    op.create_unique_constraint(
        "uq_project_link_huly_issue",
        "issue_mapping",
        ["project_link_id", "huly_issue_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_project_link_huly_issue",
        "issue_mapping",
        type_="unique",
    )
    op.drop_constraint(
        "uq_project_link_gitlab_issue",
        "issue_mapping",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_gitlab_issue_mapping",
        "issue_mapping",
        ["gitlab_project_id", "gitlab_issue_id"],
    )

    op.drop_index(
        "ix_issue_mapping_project_link_id",
        table_name="issue_mapping",
    )
    op.drop_index(
        "ix_issue_mapping_user_id",
        table_name="issue_mapping",
    )

    op.drop_constraint(
        "fk_issue_mapping_project_link_id",
        "issue_mapping",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_issue_mapping_user_id",
        "issue_mapping",
        type_="foreignkey",
    )

    op.drop_column(
        "issue_mapping",
        "project_link_id",
    )
    op.drop_column(
        "issue_mapping",
        "user_id",
    )

    op.drop_index(
        "ix_project_links_huly_project_id",
        table_name="project_links",
    )
    op.drop_index(
        "ix_project_links_gitlab_project_id",
        table_name="project_links",
    )
    op.drop_index(
        "ix_project_links_user_id",
        table_name="project_links",
    )
    op.drop_index(
        "ix_project_links_id",
        table_name="project_links",
    )

    op.drop_table("project_links")
