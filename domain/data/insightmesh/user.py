"""
InsightMesh user model.
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase


class InsightMeshUser(InsightMeshBase):
    """InsightMesh internal user model"""
    __tablename__ = "insightmesh_users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    user_metadata = Column(JSON)
    openwebui_id = Column(String)  # Removed ForeignKey since users table doesn't exist in insightmesh 