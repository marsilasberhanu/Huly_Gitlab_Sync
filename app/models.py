from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from datetime import datetime
from .database import Base

class IssueMapping(Base):
    __tablename__ = "issue_mapping"
    id = Column(Integer, primary_key=True, index=True)
    gitlab_issue_id = Column(String, unique=True, index=True, nullable=False)
    huly_issue_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommentMapping(Base):
    __tablename__ = "comment_mapping"
    id = Column(Integer, primary_key=True, index=True)
    gitlab_comment_id = Column(String, unique=True, index=True, nullable=False)
    huly_comment_id = Column(String, unique=True, index=True, nullable=False)
    issue_mapping_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SyncLog(Base):
    __tablename__ = "sync_log"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False) 
    action = Column(String, nullable=False) 
    status = Column(String, nullable=False) 
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class SyncState(Base):
    __tablename__ = "sync_state"
    id = Column(Integer, primary_key=True, index=True)
    last_sync_timestamp = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)