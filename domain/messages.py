"""
Message domain model.

Messages sent or received by people across different platforms.
This domain object wraps underlying data objects (Slack, email, etc.) 
and presents them as a single unified concept.
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MessageSchema:
    """Schema definitions for Message across different storage systems"""
    sql_insightmesh: str = "messages"
    sql_slack: str = "slack_messages"
    neo4j: str = "(:Message)"
    elastic: str = "message_index"


@dataclass
class MessagePermissions:
    """Permission configuration for Message domain"""
    default: str = "read"
    roles: List[str] = None
    scopes: Dict[str, str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ["analyst", "support"]
        if self.scopes is None:
            self.scopes = {
                "user": "own_messages_only",
                "admin": "all_messages"
            }


@dataclass
class MessageSource:
    """Data source configuration for Message"""
    database: Optional[str] = None
    table: Optional[str] = None
    elastic_index: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    query_fields: Optional[List[str]] = None


@dataclass
class MessageRelationship:
    """Represents a relationship between Message and other domains"""
    domain: str
    type: str
    foreign_key: Optional[str] = None
    through: Optional[str] = None


class Message:
    """
    Message domain model representing messages across different platforms.
    
    This model wraps underlying data objects (SlackMessage, EmailMessage, etc.)
    and presents them as a unified concept with consistent business logic.
    """
    
    def __init__(self, 
                 id: str,
                 content: str,
                 user_id: str,
                 channel_id: Optional[str] = None,
                 platform: str = "slack",
                 subject: Optional[str] = None,
                 body: Optional[str] = None,
                 thread_id: Optional[str] = None,
                 timestamp: Optional[datetime] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 _data_object: Optional[Any] = None):
        self.id = id
        self.content = content
        self.user_id = user_id
        self.channel_id = channel_id
        self.platform = platform
        self.subject = subject
        self.body = body or content  # body defaults to content if not provided
        self.thread_id = thread_id
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        
        # Store reference to underlying data object
        self._data_object = _data_object
        
        # Define schema mappings
        self.schema = MessageSchema()
        
        # Define permissions
        self.permissions = MessagePermissions()
        
        # Define data sources
        self.sources = [
            MessageSource(
                database="slack",
                table="slack_messages",
                filters={"user_id": "$person.id"}
            ),
            MessageSource(
                database="insightmesh",
                table="messages",
                filters={"user_id": "$person.id"}
            ),
            MessageSource(
                elastic_index="message_index",
                query_fields=["content", "subject", "body"]
            )
        ]
        
        # Define relationships
        self.relationships = [
            MessageRelationship(
                domain="person",
                type="belongs_to",
                foreign_key="user_id"
            ),
            MessageRelationship(
                domain="channels",
                type="belongs_to",
                foreign_key="channel_id"
            )
        ]
        
        # Context areas this domain participates in
        self.contexts = ["conversations", "channels", "threads"]
    
    @classmethod
    def from_slack_message(cls, slack_msg) -> 'Message':
        """
        Create a Message domain object from a Slack data object.
        
        Args:
            slack_msg: SlackMessage data object from domain.data.slack
        """
        return cls(
            id=slack_msg.id,
            content=slack_msg.text or slack_msg.content or "",
            user_id=slack_msg.user_id,
            channel_id=getattr(slack_msg, 'channel_id', None),
            platform="slack",
            thread_id=getattr(slack_msg, 'thread_ts', None),
            timestamp=getattr(slack_msg, 'timestamp', None) or getattr(slack_msg, 'created_at', None),
            metadata={
                'slack_ts': getattr(slack_msg, 'ts', None),
                'slack_thread_ts': getattr(slack_msg, 'thread_ts', None),
                'slack_channel': getattr(slack_msg, 'channel', None)
            },
            _data_object=slack_msg
        )
    
    @classmethod
    def from_insightmesh_message(cls, im_msg) -> 'Message':
        """
        Create a Message domain object from an InsightMesh data object.
        
        Args:
            im_msg: Message data object from domain.data.insightmesh
        """
        return cls(
            id=im_msg.id,
            content=im_msg.content,
            user_id=im_msg.user_id,
            platform="insightmesh",
            timestamp=im_msg.created_at,
            metadata={
                'conversation_id': getattr(im_msg, 'conversation_id', None),
                'role': getattr(im_msg, 'role', None)
            },
            _data_object=im_msg
        )
    
    @classmethod
    def from_email(cls, email_data: Dict[str, Any]) -> 'Message':
        """
        Create a Message domain object from email data.
        
        Args:
            email_data: Dictionary containing email fields
        """
        return cls(
            id=email_data.get('message_id', ''),
            content=email_data.get('body', ''),
            user_id=email_data.get('from_email', ''),
            platform="email",
            subject=email_data.get('subject'),
            body=email_data.get('body'),
            timestamp=email_data.get('date'),
            metadata={
                'to': email_data.get('to', []),
                'cc': email_data.get('cc', []),
                'bcc': email_data.get('bcc', []),
                'thread_id': email_data.get('thread_id')
            },
            _data_object=email_data
        )
    
    @classmethod
    async def get_for_user(cls, 
                          user_id: str, 
                          sources: Optional[List[str]] = None,
                          limit: int = 50,
                          session_factories: Optional[Dict[str, Any]] = None) -> List['Message']:
        """
        Get messages for a user across multiple data sources.
        
        This method demonstrates how domain objects can aggregate
        data from multiple underlying sources.
        """
        sources = sources or ['slack', 'insightmesh']
        session_factories = session_factories or {}
        messages = []
        
        for source in sources:
            if source == 'slack' and 'slack' in session_factories:
                slack_messages = await cls._get_slack_messages(user_id, limit, session_factories['slack'])
                messages.extend(slack_messages)
            elif source == 'insightmesh' and 'insightmesh' in session_factories:
                im_messages = await cls._get_insightmesh_messages(user_id, limit, session_factories['insightmesh'])
                messages.extend(im_messages)
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp, reverse=True)
        return messages[:limit]
    
    @classmethod
    async def _get_slack_messages(cls, user_id: str, limit: int, session_factory) -> List['Message']:
        """Get messages from Slack data source and convert to domain objects."""
        messages = []
        
        try:
            # In a real implementation with proper imports:
            # async with session_factory() as session:
            #     from domain.data.slack import SlackMessage
            #     result = await session.execute(
            #         select(SlackMessage)
            #         .where(SlackMessage.user_id == user_id)
            #         .order_by(SlackMessage.timestamp.desc())
            #         .limit(limit)
            #     )
            #     
            #     for slack_msg in result.scalars():
            #         domain_msg = cls.from_slack_message(slack_msg)
            #         messages.append(domain_msg)
            pass
        except Exception as e:
            # Log error but don't fail the whole operation
            print(f"Error fetching Slack messages: {e}")
        
        return messages
    
    @classmethod
    async def _get_insightmesh_messages(cls, user_id: str, limit: int, session_factory) -> List['Message']:
        """Get messages from InsightMesh data source and convert to domain objects."""
        messages = []
        
        try:
            # In a real implementation:
            # async with session_factory() as session:
            #     from domain.data.insightmesh import Message as IMMessage
            #     result = await session.execute(
            #         select(IMMessage)
            #         .where(IMMessage.user_id == user_id)
            #         .order_by(IMMessage.created_at.desc())
            #         .limit(limit)
            #     )
            #     
            #     for im_msg in result.scalars():
            #         domain_msg = cls.from_insightmesh_message(im_msg)
            #         messages.append(domain_msg)
            pass
        except Exception as e:
            print(f"Error fetching InsightMesh messages: {e}")
        
        return messages
    
    def get_author(self) -> Optional['Person']:
        """Get the person who sent this message"""
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def get_channel(self) -> Optional['Channel']:
        """Get the channel this message was sent in"""
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def get_thread_messages(self) -> List['Message']:
        """Get all messages in the same thread"""
        if not self.thread_id:
            return []
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def has_permission(self, action: str, role: str = None, user_id: str = None) -> bool:
        """Check if user has permission for a given action on this message"""
        if role and role in self.permissions.roles:
            if role == "admin":
                return True
            elif role == "user" and user_id == self.user_id:
                return True
        return action == self.permissions.default
    
    def get_schema_for_storage(self, storage_type: str) -> str:
        """Get the appropriate schema/table name for a storage system"""
        schema_map = {
            'sql_insightmesh': self.schema.sql_insightmesh,
            'sql_slack': self.schema.sql_slack,
            'neo4j': self.schema.neo4j,
            'elastic': self.schema.elastic
        }
        return schema_map.get(storage_type, self.schema.sql_insightmesh)
    
    def is_in_thread(self) -> bool:
        """Check if message is part of a thread"""
        return self.thread_id is not None
    
    def is_direct_message(self) -> bool:
        """Check if message is a direct message (no channel)"""
        return self.channel_id is None
    
    def get_source_config(self, source_type: str) -> Optional[MessageSource]:
        """Get configuration for a specific data source"""
        for source in self.sources:
            if source.database == source_type or source.elastic_index == source_type:
                return source
        return None
    
    def search_content(self, query: str) -> bool:
        """Check if message content matches a search query"""
        search_fields = [self.content, self.subject, self.body]
        query_lower = query.lower()
        return any(field and query_lower in field.lower() for field in search_fields if field)
    
    def get_data_object(self):
        """Get the underlying data object (SlackMessage, IMMessage, etc.)"""
        return self._data_object
    
    def sync_to_data_object(self):
        """Sync domain object changes back to the underlying data object"""
        if self._data_object:
            # Update the underlying data object with domain changes
            if hasattr(self._data_object, 'content'):
                self._data_object.content = self.content
            if hasattr(self._data_object, 'text'):
                self._data_object.text = self.content
            # Add more field mappings as needed
    
    def is_from_platform(self, platform: str) -> bool:
        """Check if message is from a specific platform"""
        return self.platform.lower() == platform.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation"""
        return {
            'id': self.id,
            'content': self.content,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'platform': self.platform,
            'subject': self.subject,
            'body': self.body,
            'thread_id': self.thread_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'contexts': self.contexts
        }
    
    def __repr__(self) -> str:
        return f"Message(id='{self.id}', user_id='{self.user_id}', platform='{self.platform}')" 