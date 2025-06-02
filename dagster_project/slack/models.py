import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class SlackUser(Base):
    """SQLAlchemy model for Slack users."""
    __tablename__ = 'slack_users'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    real_name = Column(String(255))
    display_name = Column(String(255))
    email = Column(String(255), unique=True)
    is_admin = Column(Boolean, default=False)
    is_owner = Column(Boolean, default=False)
    is_bot = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    team_id = Column(String(255))
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackUser(id='{self.id}', name='{self.name}', email='{self.email}')>"


class SlackChannel(Base):
    """SQLAlchemy model for Slack channels."""
    __tablename__ = 'slack_channels'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    is_private = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created = Column(DateTime(timezone=True))
    creator = Column(String(255))
    num_members = Column(Integer, default=0)
    purpose = Column(Text)
    topic = Column(Text)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackChannel(id='{self.id}', name='{self.name}')>" 