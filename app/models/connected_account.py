from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider = Column(
        String(50),
        nullable=False,
    )

    access_token = Column(
        String,
        nullable=False,
    )

    base_url = Column(
        String(500),
        nullable=True,
    )

    workspace_id = Column(
        String(255),
        nullable=True,
    )

    is_connected = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    user = relationship(
        "User",
        back_populates="connected_accounts",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_connected_account_user_provider",
        ),
    )