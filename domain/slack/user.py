"""
Slack user model.
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .base import SlackBase


class SlackUser(SlackBase):
    """Slack user model"""
    __tablename__ = 'slack_users'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    real_name = Column(String(255))
    display_name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    is_admin = Column(Boolean)
    is_owner = Column(Boolean)
    is_bot = Column(Boolean)
    deleted = Column(Boolean)
    team_id = Column(String(255))
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackUser(id='{self.id}', name='{self.name}', email='{self.email}')>" 