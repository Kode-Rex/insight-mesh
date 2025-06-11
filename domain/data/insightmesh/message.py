"""
Message model with multi-store capabilities.
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from .base import InsightMeshBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship


@neo4j_node(
    label="Message",
    exclude_fields=['message_metadata', 'created_at'],
    id_field='id'
)
@neo4j_relationship(
    type="BELONGS_TO_CONVERSATION",
    target_model="Conversation",
    source_field="conversation_id"
)
@neo4j_relationship(
    type="AUTHORED_BY",
    target_model="InsightMeshUser",
    source_field="user_id",
    condition="role == 'user'"  # Only create relationship for user messages
)
@elasticsearch_index(
    index_name="messages",
    text_fields=['content'],
    exclude_fields=['message_metadata']
)
class Message(InsightMeshBase):
    """Message storage with Neo4j and Elasticsearch capabilities"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    user_id = Column(String, ForeignKey("insightmesh_users.id"), index=True, nullable=True)  # Only for user messages
    role = Column(String)  # user, assistant, system
    content = Column(Text)  # Changed to Text for longer content
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    message_metadata = Column(JSON)
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if self.content and len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role='{self.role}', content='{content_preview}')>"
    
    # Business logic methods
    def is_user_message(self):
        """Check if message is from user."""
        return self.role == 'user'
    
    def is_assistant_message(self):
        """Check if message is from assistant."""
        return self.role == 'assistant'
    
    def is_system_message(self):
        """Check if message is a system message."""
        return self.role == 'system'
    
    @property
    def content_preview(self):
        """Get a preview of the message content."""
        if not self.content:
            return ""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content
    
    def get_message_summary(self):
        """Get message summary for display."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'role': self.role,
            'content_preview': self.content_preview,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.message_metadata or {}
        } 