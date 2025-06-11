"""
InsightMesh domain models package with multi-store capabilities.
"""

from .base import InsightMeshBase
from .user import InsightMeshUser
from .context import Context
from .conversation import Conversation
from .message import Message
from weave.bin.modules.annotations.sync import enable_auto_sync_for_model

# Enable automatic synchronization for all models
enable_auto_sync_for_model(InsightMeshUser)
enable_auto_sync_for_model(Context)
enable_auto_sync_for_model(Conversation)
enable_auto_sync_for_model(Message)

__all__ = [
    'InsightMeshBase',
    'InsightMeshUser', 
    'Context',
    'Conversation',
    'Message'
] 