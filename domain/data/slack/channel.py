"""
Slack channel model with multi-store capabilities.
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, Text
from sqlalchemy.sql import func
from .base import SlackBase
from weave.bin.modules.annotations import neo4j_node, elasticsearch_index, neo4j_relationship


@neo4j_node(
    label="SlackChannel",
    exclude_fields=['data', 'created_at', 'updated_at'],
    id_field='id'
)
@neo4j_relationship(
    type="CREATED_BY",
    target_model="SlackUser",  # Will be resolved at runtime
    source_field="creator"
)
@elasticsearch_index(
    index_name="slack_channels",
    text_fields=['name', 'purpose', 'topic'],
    exclude_fields=['data']
)
class SlackChannel(SlackBase):
    """Slack channel model with Neo4j and Elasticsearch capabilities"""
    __tablename__ = 'slack_channels'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    is_private = Column(Boolean)
    is_archived = Column(Boolean)
    created = Column(DateTime(timezone=True))
    creator = Column(String(255))  # References SlackUser.id
    num_members = Column(Integer)
    purpose = Column(Text)
    topic = Column(Text)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackChannel(id='{self.id}', name='{self.name}')>"
    
    # Business logic methods
    def is_active_channel(self):
        """Check if channel is active (not archived)."""
        return not self.is_archived
    
    @property
    def display_info(self):
        """Get channel display information."""
        privacy = "Private" if self.is_private else "Public"
        status = "Archived" if self.is_archived else "Active"
        return f"{self.name} ({privacy}, {status}, {self.num_members or 0} members)" 