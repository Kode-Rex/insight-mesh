"""
Slack user model with multi-store capabilities.
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .base import SlackBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship, SyncMixin


@neo4j_node(
    label="SlackUser",
    exclude_fields=['data', 'created_at', 'updated_at'],  # Exclude complex/meta fields
    id_field='id'
)
@elasticsearch_index(
    index_name="slack_users",
    text_fields=['name', 'real_name', 'display_name'],  # Fields for full-text search
    exclude_fields=['data']  # Exclude JSON field from search
)
class SlackUser(SlackBase, SyncMixin):
    """Slack user model with Neo4j and Elasticsearch capabilities"""
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
    
    # Business logic methods can still be added here
    @property
    def display_name_or_name(self):
        """Get display name or fall back to name."""
        return self.display_name or self.name or self.real_name
    
    def is_active_user(self):
        """Check if user is active (not deleted and not a bot)."""
        return not self.deleted and not self.is_bot 