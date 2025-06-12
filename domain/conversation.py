"""
Conversation domain model - composes related messages from multiple sources.

This domain object represents business conversations that can span multiple
platforms and sources, providing unified access to related messages with
business-relevant filtering and aggregation.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Import the data layer models
from domain.data.insightmesh import Conversation as InsightMeshConversation, Message as InsightMeshMessage
from domain.data.slack import SlackChannel


class ConversationType(Enum):
    """Types of conversations in the system"""
    CHAT_SESSION = "chat_session"      # InsightMesh AI chat session
    SLACK_THREAD = "slack_thread"      # Slack thread conversation
    SLACK_CHANNEL = "slack_channel"    # Slack channel discussion
    EMAIL_THREAD = "email_thread"      # Email conversation thread
    CROSS_PLATFORM = "cross_platform"  # Conversation spanning multiple platforms


@dataclass
class ConversationIdentity:
    """Represents a conversation's identity and scope"""
    primary_id: str
    title: str
    conversation_type: ConversationType
    participants: List[str]  # User IDs
    topic: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class Conversation:
    """
    Domain Conversation - composes related messages from multiple sources.
    
    This class provides business-focused conversation management, aggregating
    messages from different platforms around topics, participants, and timeframes.
    """
    
    def __init__(self, identity: ConversationIdentity):
        self.identity = identity
        self._insightmesh_conversation: Optional[InsightMeshConversation] = None
        self._insightmesh_messages: List[InsightMeshMessage] = []
        self._slack_messages: List[Any] = []  # Would be SlackMessage when available
        self._email_messages: List[Dict[str, Any]] = []
        self._loaded_sources: set = set()
    
    @classmethod
    async def from_insightmesh_conversation(cls, im_conversation: InsightMeshConversation, 
                                          session_factories: Dict[str, Any] = None) -> 'Conversation':
        """Create Conversation domain object from InsightMesh conversation."""
        identity = ConversationIdentity(
            primary_id=str(im_conversation.id),
            title=im_conversation.display_title,
            conversation_type=ConversationType.CHAT_SESSION,
            participants=[im_conversation.user_id] if im_conversation.user_id else [],
            topic=im_conversation.title,
            start_date=im_conversation.created_at,
            end_date=im_conversation.updated_at
        )
        
        conversation = cls(identity)
        conversation._insightmesh_conversation = im_conversation
        conversation._loaded_sources.add('insightmesh')
        
        # Load related messages
        await conversation._load_insightmesh_messages(session_factories)
        
        return conversation
    
    @classmethod
    async def from_slack_channel(cls, slack_channel: SlackChannel, 
                                date_range: tuple = None,
                                session_factories: Dict[str, Any] = None) -> 'Conversation':
        """Create Conversation domain object from Slack channel activity."""
        start_date, end_date = date_range or (None, None)
        
        identity = ConversationIdentity(
            primary_id=f"slack_channel_{slack_channel.id}",
            title=f"#{slack_channel.name}",
            conversation_type=ConversationType.SLACK_CHANNEL,
            participants=[],  # Would be loaded from channel membership
            topic=slack_channel.purpose or slack_channel.topic,
            start_date=start_date,
            end_date=end_date
        )
        
        conversation = cls(identity)
        conversation._loaded_sources.add('slack')
        
        # Load channel messages (when SlackMessage model exists)
        # await conversation._load_slack_channel_messages(slack_channel.id, date_range, session_factories)
        
        return conversation
    
    @classmethod
    async def create_cross_platform_conversation(cls, title: str, participants: List[str],
                                               topic: str = None, date_range: tuple = None,
                                               session_factories: Dict[str, Any] = None) -> 'Conversation':
        """
        Create a cross-platform conversation by aggregating messages from multiple sources.
        
        This is the key business method - it finds related messages across platforms
        based on participants, timeframe, and topic similarity.
        """
        start_date, end_date = date_range or (None, None)
        
        identity = ConversationIdentity(
            primary_id=f"cross_platform_{hash((tuple(participants), topic, start_date))}",
            title=title,
            conversation_type=ConversationType.CROSS_PLATFORM,
            participants=participants,
            topic=topic,
            start_date=start_date,
            end_date=end_date
        )
        
        conversation = cls(identity)
        
        # Load messages from all sources for these participants
        await conversation._load_cross_platform_messages(participants, date_range, topic, session_factories)
        
        return conversation
    
    @classmethod
    async def find_conversations_by_topic(cls, topic: str, date_range: tuple = None,
                                        session_factories: Dict[str, Any] = None) -> List['Conversation']:
        """Find conversations across all platforms related to a topic."""
        conversations = []
        start_date, end_date = date_range or (None, None)
        
        # Search InsightMesh conversations
        if session_factories and 'insightmesh' in session_factories:
            im_session = session_factories['insightmesh']
            query = im_session.query(InsightMeshConversation)
            
            # Filter by topic in title
            if topic:
                query = query.filter(InsightMeshConversation.title.ilike(f'%{topic}%'))
            
            # Filter by date range
            if start_date:
                query = query.filter(InsightMeshConversation.created_at >= start_date)
            if end_date:
                query = query.filter(InsightMeshConversation.created_at <= end_date)
            
            im_conversations = query.all()
            for im_conv in im_conversations:
                domain_conv = await cls.from_insightmesh_conversation(im_conv, session_factories)
                conversations.append(domain_conv)
        
        # Search Slack channels (when implemented)
        # if session_factories and 'slack' in session_factories:
        #     slack_channels = await cls._find_slack_conversations_by_topic(topic, date_range, session_factories)
        #     conversations.extend(slack_channels)
        
        return conversations
    
    async def _load_insightmesh_messages(self, session_factories: Dict[str, Any] = None):
        """Load messages for the InsightMesh conversation."""
        if not self._insightmesh_conversation or not session_factories:
            return
        
        im_session = session_factories.get('insightmesh')
        if im_session:
            messages = im_session.query(InsightMeshMessage).filter_by(
                conversation_id=self._insightmesh_conversation.id
            ).order_by(InsightMeshMessage.created_at).all()
            
            self._insightmesh_messages = messages
            
            # Update participants from messages
            user_ids = set()
            for msg in messages:
                if msg.user_id:
                    user_ids.add(msg.user_id)
            
            self.identity.participants.extend(list(user_ids))
            self.identity.participants = list(set(self.identity.participants))  # Remove duplicates
    
    async def _load_cross_platform_messages(self, participants: List[str], date_range: tuple,
                                          topic: str, session_factories: Dict[str, Any] = None):
        """Load messages from all platforms for the given participants and criteria."""
        if not session_factories:
            return
        
        start_date, end_date = date_range or (None, None)
        
        # Load from InsightMesh
        if 'insightmesh' in session_factories:
            im_session = session_factories['insightmesh']
            
            # Find conversations for these participants
            query = im_session.query(InsightMeshConversation).filter(
                InsightMeshConversation.user_id.in_(participants)
            )
            
            if start_date:
                query = query.filter(InsightMeshConversation.created_at >= start_date)
            if end_date:
                query = query.filter(InsightMeshConversation.created_at <= end_date)
            if topic:
                query = query.filter(InsightMeshConversation.title.ilike(f'%{topic}%'))
            
            im_conversations = query.all()
            
            # Load messages from these conversations
            for conv in im_conversations:
                messages = im_session.query(InsightMeshMessage).filter_by(
                    conversation_id=conv.id
                ).all()
                self._insightmesh_messages.extend(messages)
            
            self._loaded_sources.add('insightmesh')
        
        # Load from Slack (when implemented)
        # if 'slack' in session_factories:
        #     slack_messages = await self._load_slack_messages_for_participants(
        #         participants, date_range, topic, session_factories['slack']
        #     )
        #     self._slack_messages.extend(slack_messages)
        #     self._loaded_sources.add('slack')
    
    # Business Logic Properties
    @property
    def message_count(self) -> int:
        """Get total number of messages in this conversation."""
        return (len(self._insightmesh_messages) + 
                len(self._slack_messages) + 
                len(self._email_messages))
    
    @property
    def participant_count(self) -> int:
        """Get number of unique participants."""
        return len(set(self.identity.participants))
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get conversation duration."""
        if self.identity.start_date and self.identity.end_date:
            return self.identity.end_date - self.identity.start_date
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if conversation is currently active."""
        if self._insightmesh_conversation:
            return self._insightmesh_conversation.is_active_conversation()
        
        # For other types, consider active if recent activity
        if self.identity.end_date:
            return (datetime.utcnow() - self.identity.end_date) < timedelta(days=7)
        
        return True
    
    # Business Logic Methods
    def get_messages_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get messages within a specific date range."""
        messages = []
        
        # Filter InsightMesh messages
        for msg in self._insightmesh_messages:
            if msg.created_at and start_date <= msg.created_at <= end_date:
                messages.append({
                    'id': str(msg.id),
                    'content': msg.content,
                    'author_id': msg.user_id,
                    'timestamp': msg.created_at,
                    'role': msg.role,
                    'platform': 'insightmesh',
                    'source_data': msg
                })
        
        # Filter Slack messages (when implemented)
        # for msg in self._slack_messages:
        #     if msg.timestamp and start_date <= msg.timestamp <= end_date:
        #         messages.append({...})
        
        # Sort by timestamp
        messages.sort(key=lambda m: m['timestamp'])
        return messages
    
    def get_messages_by_participant(self, participant_id: str) -> List[Dict[str, Any]]:
        """Get all messages from a specific participant."""
        messages = []
        
        for msg in self._insightmesh_messages:
            if msg.user_id == participant_id:
                messages.append({
                    'id': str(msg.id),
                    'content': msg.content,
                    'author_id': msg.user_id,
                    'timestamp': msg.created_at,
                    'role': msg.role,
                    'platform': 'insightmesh',
                    'source_data': msg
                })
        
        messages.sort(key=lambda m: m['timestamp'])
        return messages
    
    def get_user_messages_only(self) -> List[Dict[str, Any]]:
        """Get only user-authored messages (exclude AI responses)."""
        messages = []
        
        for msg in self._insightmesh_messages:
            if msg.is_user_message():
                messages.append({
                    'id': str(msg.id),
                    'content': msg.content,
                    'author_id': msg.user_id,
                    'timestamp': msg.created_at,
                    'platform': 'insightmesh',
                    'source_data': msg
                })
        
        messages.sort(key=lambda m: m['timestamp'])
        return messages
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the conversation."""
        all_messages = self.get_all_messages()
        
        return {
            'identity': {
                'id': self.identity.primary_id,
                'title': self.identity.title,
                'type': self.identity.conversation_type.value,
                'topic': self.identity.topic
            },
            'participants': {
                'count': self.participant_count,
                'user_ids': self.identity.participants
            },
            'timeline': {
                'start_date': self.identity.start_date.isoformat() if self.identity.start_date else None,
                'end_date': self.identity.end_date.isoformat() if self.identity.end_date else None,
                'duration_hours': self.duration.total_seconds() / 3600 if self.duration else None
            },
            'activity': {
                'total_messages': self.message_count,
                'user_messages': len(self.get_user_messages_only()),
                'is_active': self.is_active
            },
            'sources': list(self._loaded_sources),
            'first_message': all_messages[0] if all_messages else None,
            'last_message': all_messages[-1] if all_messages else None
        }
    
    def get_all_messages(self) -> List[Dict[str, Any]]:
        """Get all messages from all sources, sorted by timestamp."""
        messages = []
        
        # Add InsightMesh messages
        for msg in self._insightmesh_messages:
            messages.append({
                'id': str(msg.id),
                'content': msg.content,
                'author_id': msg.user_id,
                'timestamp': msg.created_at,
                'role': msg.role,
                'platform': 'insightmesh',
                'source_data': msg
            })
        
        # Add Slack messages (when implemented)
        # for msg in self._slack_messages:
        #     messages.append({...})
        
        # Sort by timestamp
        messages.sort(key=lambda m: m['timestamp'] if m['timestamp'] else datetime.min)
        return messages
    
    # Data Access
    def get_insightmesh_conversation(self) -> Optional[InsightMeshConversation]:
        """Get the underlying InsightMesh conversation data object."""
        return self._insightmesh_conversation
    
    def get_insightmesh_messages(self) -> List[InsightMeshMessage]:
        """Get the underlying InsightMesh message data objects."""
        return self._insightmesh_messages
    
    def has_source(self, source: str) -> bool:
        """Check if conversation has data from a specific source."""
        return source in self._loaded_sources
    
    def get_loaded_sources(self) -> List[str]:
        """Get list of sources that have been loaded."""
        return list(self._loaded_sources)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'identity': {
                'id': self.identity.primary_id,
                'title': self.identity.title,
                'type': self.identity.conversation_type.value,
                'topic': self.identity.topic,
                'participants': self.identity.participants
            },
            'timeline': {
                'start_date': self.identity.start_date.isoformat() if self.identity.start_date else None,
                'end_date': self.identity.end_date.isoformat() if self.identity.end_date else None,
                'duration_hours': self.duration.total_seconds() / 3600 if self.duration else None
            },
            'activity': {
                'message_count': self.message_count,
                'participant_count': self.participant_count,
                'is_active': self.is_active
            },
            'sources': self.get_loaded_sources()
        }
    
    def __repr__(self) -> str:
        return f"Conversation(id='{self.identity.primary_id}', title='{self.identity.title}', type='{self.identity.conversation_type.value}', messages={self.message_count})" 