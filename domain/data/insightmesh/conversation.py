"""
Conversation model for tracking conversations.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase


class Conversation(InsightMeshBase):
    """Conversation tracking"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("insightmesh_users.id"), index=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    conversation_metadata = Column(JSON) 