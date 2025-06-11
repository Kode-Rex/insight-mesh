"""
Context model with multi-store capabilities.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import InsightMeshBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship


@neo4j_node(
    label="Context",
    exclude_fields=['content', 'context_metadata', 'created_at', 'expires_at'],
    id_field='id'
)
@neo4j_relationship(
    type="BELONGS_TO_USER",
    target_model="InsightMeshUser",
    source_field="user_id"
)
@elasticsearch_index(
    index_name="contexts",
    text_fields=[],  # Context content is usually structured, not for text search
    exclude_fields=['content', 'context_metadata']
)
class Context(InsightMeshBase):
    """Context storage for user sessions with Neo4j and Elasticsearch capabilities"""
    __tablename__ = "contexts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("insightmesh_users.id"), index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean)
    context_metadata = Column(JSON)
    
    def __repr__(self):
        return f"<Context(id={self.id}, user_id='{self.user_id}', is_active={self.is_active})>"
    
    # Business logic methods
    def is_expired(self):
        """Check if context has expired."""
        if not self.expires_at:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self):
        """Check if context is valid (active and not expired)."""
        return self.is_active and not self.is_expired()
    
    def get_context_size(self):
        """Get the size of the context content."""
        if not self.content:
            return 0
        import json
        return len(json.dumps(self.content))
    
    @property
    def context_type(self):
        """Get the type of context from metadata."""
        if not self.context_metadata:
            return "unknown"
        return self.context_metadata.get('type', 'unknown')
    
    def get_context_summary(self):
        """Get context summary for display."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.context_type,
            'is_active': self.is_active,
            'is_expired': self.is_expired(),
            'size': self.get_context_size(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        } 