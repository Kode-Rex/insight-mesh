"""
Message model for conversation messages.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from .base import InsightMeshBase


class Message(InsightMeshBase):
    """Message storage for conversations"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String)  # user, assistant, system
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    message_metadata = Column(JSON) 