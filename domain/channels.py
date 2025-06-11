"""
Channel domain model.

Communication channels across different platforms (Slack, Teams, etc.).
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChannelSchema:
    """Schema definitions for Channel across different storage systems"""
    sql_slack: str = "slack_channels"
    neo4j: str = "(:Channel)"
    elastic: str = "channel_index"


@dataclass
class ChannelPermissions:
    """Permission configuration for Channel domain"""
    default: str = "read"
    roles: List[str] = None
    scopes: Dict[str, str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ["member", "admin"]
        if self.scopes is None:
            self.scopes = {
                "member": "joined_channels_only",
                "admin": "all_channels"
            }


@dataclass
class ChannelSource:
    """Data source configuration for Channel"""
    database: Optional[str] = None
    table: Optional[str] = None
    elastic_index: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    query_fields: Optional[List[str]] = None


@dataclass
class ChannelRelationship:
    """Represents a relationship between Channel and other domains"""
    domain: str
    type: str
    foreign_key: Optional[str] = None
    through: Optional[str] = None


class Channel:
    """
    Channel domain model representing communication channels.
    
    This model encapsulates the business logic and relationships for channels,
    including their connections to messages and people.
    """
    
    def __init__(self, 
                 id: str,
                 name: str,
                 platform: str = "slack",
                 purpose: Optional[str] = None,
                 topic: Optional[str] = None,
                 is_archived: bool = False,
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.platform = platform
        self.purpose = purpose
        self.topic = topic
        self.is_archived = is_archived
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        
        # Define schema mappings
        self.schema = ChannelSchema()
        
        # Define permissions
        self.permissions = ChannelPermissions()
        
        # Define data sources
        self.sources = [
            ChannelSource(
                database="slack",
                table="slack_channels",
                filters={"is_archived": False}
            ),
            ChannelSource(
                elastic_index="channel_index",
                query_fields=["name", "purpose", "topic"]
            )
        ]
        
        # Define relationships
        self.relationships = [
            ChannelRelationship(
                domain="messages",
                type="has_many",
                foreign_key="channel_id"
            ),
            ChannelRelationship(
                domain="person",
                type="has_many",
                through="channel_members"
            )
        ]
        
        # Context areas this domain participates in
        self.contexts = ["messages", "members", "activity"]
    
    def get_messages(self) -> List['Message']:
        """Get all messages in this channel"""
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def get_members(self) -> List['Person']:
        """Get all members of this channel"""
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def has_permission(self, action: str, role: str = None, user_id: str = None) -> bool:
        """Check if user has permission for a given action on this channel"""
        if role and role in self.permissions.roles:
            if role == "admin":
                return True
            elif role == "member":
                # Would need to check if user is actually a member of this channel
                return True
        return action == self.permissions.default
    
    def get_schema_for_storage(self, storage_type: str) -> str:
        """Get the appropriate schema/table name for a storage system"""
        schema_map = {
            'sql_slack': self.schema.sql_slack,
            'neo4j': self.schema.neo4j,
            'elastic': self.schema.elastic
        }
        return schema_map.get(storage_type, self.schema.sql_slack)
    
    def is_active(self) -> bool:
        """Check if channel is active (not archived)"""
        return not self.is_archived
    
    def get_source_config(self, source_type: str) -> Optional[ChannelSource]:
        """Get configuration for a specific data source"""
        for source in self.sources:
            if source.database == source_type or source.elastic_index == source_type:
                return source
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert channel to dictionary representation"""
        return {
            'id': self.id,
            'name': self.name,
            'platform': self.platform,
            'purpose': self.purpose,
            'topic': self.topic,
            'is_archived': self.is_archived,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'contexts': self.contexts
        }
    
    def __repr__(self) -> str:
        return f"Channel(id='{self.id}', name='{self.name}', platform='{self.platform}')" 