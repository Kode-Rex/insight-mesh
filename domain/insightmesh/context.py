"""
Context model for user sessions.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase


class Context(InsightMeshBase):
    """Context storage for user sessions"""
    __tablename__ = "contexts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("insightmesh_users.id"), index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean)
    context_metadata = Column(JSON) 