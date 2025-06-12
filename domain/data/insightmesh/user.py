"""
InsightMesh user model with multi-store capabilities.
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship


@neo4j_node(
    label="InsightMeshUser",
    exclude_fields=['user_metadata', 'created_at', 'updated_at'],
    id_field='id'
)
@elasticsearch_index(
    index_name="insightmesh_users",
    text_fields=['name', 'email'],
    exclude_fields=['user_metadata', 'openwebui_id']
)
class InsightMeshUser(InsightMeshBase):
    """InsightMesh internal user model with Neo4j and Elasticsearch capabilities"""
    __tablename__ = "insightmesh_users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    user_metadata = Column(JSON)
    openwebui_id = Column(String)  # Removed ForeignKey since users table doesn't exist in insightmesh
    
    def __repr__(self):
        return f"<InsightMeshUser(id='{self.id}', email='{self.email}', name='{self.name}')>"
    
    # Business logic methods
    def is_active_user(self):
        """Check if user is active."""
        return self.is_active
    
    @property
    def display_name(self):
        """Get display name or fall back to email."""
        return self.name or self.email
    
    def get_user_context(self):
        """Get user context for personalization."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_active': self.is_active,
            'metadata': self.user_metadata or {}
        } 