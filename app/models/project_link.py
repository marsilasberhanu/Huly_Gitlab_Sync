from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.database import Base


class ProjectLink(Base):
    __tablename__ = "project_links"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    gitlab_project_id = Column(
        BigInteger,
        nullable=False,
        index=True,
    )
    gitlab_project_name = Column(
        String(255),
        nullable=True,
    )

    huly_project_id = Column(
        String(255),
        nullable=False,
        index=True,
    )
    huly_project_name = Column(
        String(255),
        nullable=True,
    )

    webhook_secret_hash = Column(
        String(64),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "gitlab_project_id",
            "huly_project_id",
            name="uq_project_link_user_projects",
        ),
    )
