"""
User domain model - composes data from multiple sources.

This domain object aggregates user data from Slack, InsightMesh, and other sources
to provide a unified business interface while keeping the underlying data models
intact for ETL processes.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from dataclasses import dataclass

# Import the data layer models
from domain.data.slack import SlackUser
from domain.data.insightmesh import InsightMeshUser


@dataclass
class UserIdentity:
    """Represents a user's identity across different systems"""
    primary_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    slack_id: Optional[str] = None
    insightmesh_id: Optional[str] = None


class User:
    """
    Domain User - composes data from multiple sources.
    
    This class provides a unified business interface for users while preserving
    the underlying data models for ETL and source-specific operations.
    """
    
    def __init__(self, identity: UserIdentity):
        self.identity = identity
        self._slack_user: Optional[SlackUser] = None
        self._insightmesh_user: Optional[InsightMeshUser] = None
        self._loaded_sources: set = set()
    
    @classmethod
    async def from_email(cls, email: str, session_factories: Dict[str, Any] = None) -> Optional['User']:
        """
        Create User domain object by finding across all data sources by email.
        
        Args:
            email: Email address to search for
            session_factories: Database session factories for different sources
        """
        identity = UserIdentity(primary_id=email, email=email)
        user = cls(identity)
        
        # Load from all available sources
        await user._load_from_sources(email=email, session_factories=session_factories)
        
        # Set primary ID based on what we found
        if user._insightmesh_user:
            identity.primary_id = user._insightmesh_user.id
            identity.insightmesh_id = user._insightmesh_user.id
        elif user._slack_user:
            identity.primary_id = user._slack_user.id
            identity.slack_id = user._slack_user.id
        
        return user if user.has_any_data() else None
    
    @classmethod
    async def from_slack_id(cls, slack_id: str, session_factories: Dict[str, Any] = None) -> Optional['User']:
        """Create User domain object from Slack ID."""
        identity = UserIdentity(primary_id=slack_id, slack_id=slack_id)
        user = cls(identity)
        await user._load_from_sources(slack_id=slack_id, session_factories=session_factories)
        return user if user.has_any_data() else None
    
    @classmethod
    async def from_insightmesh_id(cls, im_id: str, session_factories: Dict[str, Any] = None) -> Optional['User']:
        """Create User domain object from InsightMesh ID."""
        identity = UserIdentity(primary_id=im_id, insightmesh_id=im_id)
        user = cls(identity)
        await user._load_from_sources(insightmesh_id=im_id, session_factories=session_factories)
        return user if user.has_any_data() else None
    
    async def _load_from_sources(self, email: str = None, slack_id: str = None, 
                               insightmesh_id: str = None, session_factories: Dict[str, Any] = None):
        """Load user data from all available sources."""
        session_factories = session_factories or {}
        
        # Load from InsightMesh
        if email or insightmesh_id:
            try:
                im_session = session_factories.get('insightmesh')
                if im_session:
                    if email:
                        self._insightmesh_user = im_session.query(InsightMeshUser).filter_by(email=email).first()
                    elif insightmesh_id:
                        self._insightmesh_user = im_session.query(InsightMeshUser).filter_by(id=insightmesh_id).first()
                    
                    if self._insightmesh_user:
                        self._loaded_sources.add('insightmesh')
                        self.identity.insightmesh_id = self._insightmesh_user.id
                        if not self.identity.email:
                            self.identity.email = self._insightmesh_user.email
                        if not self.identity.name:
                            self.identity.name = self._insightmesh_user.name
            except Exception as e:
                print(f"Error loading from InsightMesh: {e}")
        
        # Load from Slack
        if email or slack_id:
            try:
                slack_session = session_factories.get('slack')
                if slack_session:
                    if email:
                        self._slack_user = slack_session.query(SlackUser).filter_by(email=email).first()
                    elif slack_id:
                        self._slack_user = slack_session.query(SlackUser).filter_by(id=slack_id).first()
                    
                    if self._slack_user:
                        self._loaded_sources.add('slack')
                        self.identity.slack_id = self._slack_user.id
                        if not self.identity.email:
                            self.identity.email = self._slack_user.email
                        if not self.identity.name:
                            self.identity.name = self._slack_user.display_name_or_name
            except Exception as e:
                print(f"Error loading from Slack: {e}")
    
    # Business Logic Properties
    @property
    def name(self) -> str:
        """Get the best available name from all sources."""
        if self._insightmesh_user and self._insightmesh_user.name:
            return self._insightmesh_user.name
        elif self._slack_user:
            return self._slack_user.display_name_or_name
        return self.identity.email or "Unknown User"
    
    @property
    def email(self) -> Optional[str]:
        """Get the best available email from all sources."""
        if self._insightmesh_user and self._insightmesh_user.email:
            return self._insightmesh_user.email
        elif self._slack_user and self._slack_user.email:
            return self._slack_user.email
        return self.identity.email
    
    @property
    def is_active(self) -> bool:
        """Check if user is active in any system."""
        if self._insightmesh_user and self._insightmesh_user.is_active_user():
            return True
        elif self._slack_user and self._slack_user.is_active_user():
            return True
        return False
    
    # Source Availability
    def has_slack_presence(self) -> bool:
        """Check if user has Slack data."""
        return self._slack_user is not None
    
    def has_insightmesh_account(self) -> bool:
        """Check if user has InsightMesh account."""
        return self._insightmesh_user is not None
    
    def has_any_data(self) -> bool:
        """Check if user has data from any source."""
        return len(self._loaded_sources) > 0
    
    def get_loaded_sources(self) -> List[str]:
        """Get list of sources that have been loaded."""
        return list(self._loaded_sources)
    
    # Data Access
    def get_slack_user(self) -> Optional[SlackUser]:
        """Get the underlying Slack user data object."""
        return self._slack_user
    
    def get_insightmesh_user(self) -> Optional[InsightMeshUser]:
        """Get the underlying InsightMesh user data object."""
        return self._insightmesh_user
    
    # Business Operations
    async def get_conversations(self, session_factories: Dict[str, Any] = None):
        """Get all conversations for this user from InsightMesh."""
        if not self._insightmesh_user:
            return []
        
        from domain.data.insightmesh import Conversation
        im_session = session_factories.get('insightmesh') if session_factories else None
        if im_session:
            return im_session.query(Conversation).filter_by(user_id=self._insightmesh_user.id).all()
        return []
    
    async def get_slack_channels(self, session_factories: Dict[str, Any] = None):
        """Get Slack channels this user is in (would need channel membership data)."""
        if not self._slack_user:
            return []
        
        # This would require channel membership data
        # For now, return empty list
        return []
    
    def get_user_context(self) -> Dict[str, Any]:
        """Get comprehensive user context from all sources."""
        context = {
            'identity': {
                'primary_id': self.identity.primary_id,
                'email': self.email,
                'name': self.name,
                'slack_id': self.identity.slack_id,
                'insightmesh_id': self.identity.insightmesh_id
            },
            'sources': self.get_loaded_sources(),
            'is_active': self.is_active,
            'capabilities': {
                'has_slack': self.has_slack_presence(),
                'has_insightmesh': self.has_insightmesh_account()
            }
        }
        
        # Add source-specific context
        if self._slack_user:
            context['slack'] = {
                'display_name': self._slack_user.display_name,
                'real_name': self._slack_user.real_name,
                'is_admin': self._slack_user.is_admin,
                'is_bot': self._slack_user.is_bot,
                'team_id': self._slack_user.team_id
            }
        
        if self._insightmesh_user:
            context['insightmesh'] = {
                'is_active': self._insightmesh_user.is_active,
                'openwebui_id': self._insightmesh_user.openwebui_id,
                'metadata': self._insightmesh_user.user_metadata
            }
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'identity': {
                'primary_id': self.identity.primary_id,
                'email': self.email,
                'name': self.name
            },
            'sources': self.get_loaded_sources(),
            'is_active': self.is_active,
            'has_slack': self.has_slack_presence(),
            'has_insightmesh': self.has_insightmesh_account()
        }
    
    def __repr__(self) -> str:
        sources = ', '.join(self.get_loaded_sources())
        return f"User(id='{self.identity.primary_id}', name='{self.name}', sources=[{sources}])" 