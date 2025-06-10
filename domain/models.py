"""
Domain models for the Insight Mesh project.
Contains all shared database models used across services.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, Text
from sqlalchemy.sql import func

# Create base classes for different domains
MCPBase = declarative_base()
SlackBase = declarative_base()

# ============================================================================
# MCP Domain Models
# ============================================================================

# Note: OpenWebUIUser model commented out as it's not part of the insightmesh database
# This would be in a separate OpenWebUI database if needed
# class OpenWebUIUser(MCPBase):
#     """OpenWebUI User model (matches the OpenWebUI database schema)"""
#     __tablename__ = "users"
#     
#     id = Column(String, primary_key=True)
#     email = Column(String, unique=True, index=True)
#     name = Column(String)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     is_active = Column(Boolean, default=True)
#     is_superuser = Column(Boolean, default=False)
#     is_verified = Column(Boolean, default=False)
#     hashed_password = Column(String)
#     oauth_accounts = Column(JSON, default=list)
#     settings = Column(JSON, default=dict)

class MCPUser(MCPBase):
    """MCP internal user model"""
    __tablename__ = "mcp_users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    user_metadata = Column(JSON)
    openwebui_id = Column(String)  # Removed ForeignKey since users table doesn't exist in insightmesh

class Context(MCPBase):
    """Context storage for user sessions"""
    __tablename__ = "contexts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("mcp_users.id"), index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean)
    context_metadata = Column(JSON)

class Conversation(MCPBase):
    """Conversation tracking"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("mcp_users.id"), index=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean)
    conversation_metadata = Column(JSON)

class Message(MCPBase):
    """Message storage for conversations"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String)  # user, assistant, system
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    message_metadata = Column(JSON)

# ============================================================================
# Slack Domain Models
# ============================================================================

class SlackUser(SlackBase):
    """Slack user model"""
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

class SlackChannel(SlackBase):
    """Slack channel model"""
    __tablename__ = 'slack_channels'
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    is_private = Column(Boolean)
    is_archived = Column(Boolean)
    created = Column(DateTime(timezone=True))
    creator = Column(String(255))
    num_members = Column(Integer)
    purpose = Column(Text)
    topic = Column(Text)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SlackChannel(id='{self.id}', name='{self.name}')>" 