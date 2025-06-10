"""
Slack channel model.
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from .base import SlackBase


class SlackChannel(SlackBase):
    """Slack channel model"""
    __tablename__ = 'slack_channels'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    is_private = Column(Boolean)
    is_archived = Column(Boolean)
    created = Column(DateTime(timezone=True))
    creator = Column(String(255))
    num_members = Column(Integer)
    purpose = Column(Text)
    topic = Column(Text)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackChannel(id='{self.id}', name='{self.name}')>" 