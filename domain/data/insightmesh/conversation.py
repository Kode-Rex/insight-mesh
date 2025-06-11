"""
Conversation model with multi-store capabilities.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship


@neo4j_node(
    label="Conversation",
    exclude_fields=['conversation_metadata', 'created_at', 'updated_at'],
    id_field='id'
)
@neo4j_relationship(
    type="BELONGS_TO",
    target_model="InsightMeshUser",
    source_field="user_id"
)
@elasticsearch_index(
    index_name="conversations",
    text_fields=['title'],
    exclude_fields=['conversation_metadata']
)
class Conversation(InsightMeshBase):
    """Conversation tracking with Neo4j and Elasticsearch capabilities"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("insightmesh_users.id"), index=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    conversation_metadata = Column(JSON)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', user_id='{self.user_id}')>"
    
    # Business logic methods
    def is_active_conversation(self):
        """Check if conversation is active."""
        return self.is_active
    
    @property
    def display_title(self):
        """Get display title or generate one."""
        return self.title or f"Conversation {self.id}"
    
    def get_conversation_summary(self):
        """Get conversation summary for display."""
        return {
            'id': self.id,
            'title': self.display_title,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 