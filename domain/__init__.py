"""
Domain models for InsightMesh.

This module contains business domain models that compose data from multiple
sources to provide unified business interfaces while preserving the underlying
data models for ETL processes.
"""

from .user import User, UserIdentity
from .conversation import Conversation, ConversationIdentity, ConversationType
from .document import (
    Document, DocumentIdentity, DocumentFormat, DocumentSource,
    search_google_docs, search_slack_files, 
    get_recent_google_drive_activity, get_recent_slack_files, get_recent_document_activity
)

__all__ = [
    'User', 
    'UserIdentity',
    'Conversation', 
    'ConversationIdentity',
    'ConversationType',
    'Document',
    'DocumentIdentity',
    'DocumentFormat',
    'DocumentSource',
    'search_google_docs',
    'search_slack_files',
    'get_recent_google_drive_activity',
    'get_recent_slack_files',
    'get_recent_document_activity'
] 