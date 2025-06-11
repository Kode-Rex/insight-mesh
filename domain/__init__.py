"""
Domain models for InsightMesh.

This module contains business domain models that compose data from multiple
sources to provide unified business interfaces while preserving the underlying
data models for ETL processes.
"""

from .user import User, UserIdentity
from .conversation import Conversation, ConversationIdentity, ConversationType

__all__ = [
    'User', 
    'UserIdentity',
    'Conversation', 
    'ConversationIdentity',
    'ConversationType'
] 