from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    UniqueConstraint,
    func,
)
from app.database import Base


class IssueMapping(Base):
    __tablename__ = "issue_mappings"

    id = Column(Integer, primary_key=True, index=True)

    gitlab_project_id = Column(BigInteger, nullable=False)
    gitlab_project_name = Column(String, nullable=True)

    gitlab_issue_id = Column(BigInteger, nullable=False)
    gitlab_issue_iid = Column(BigInteger, nullable=True)
    gitlab_issue_url = Column(Text, nullable=True)
    gitlab_title = Column(Text, nullable=True)

    huly_project_id = Column(String, nullable=False)
    huly_issue_id = Column(String, nullable=False)
    huly_identifier = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "gitlab_project_id",
            "gitlab_issue_id",
            name="uq_gitlab_issue_mapping",
        ),
    )