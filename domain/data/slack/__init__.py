"""
Slack domain data models with multi-store capabilities.
"""

from .base import SlackBase
from .user import SlackUser
from .channel import SlackChannel
from weave.bin.modules.annotations.sync import enable_auto_sync_for_model

# Enable automatic synchronization for all models
enable_auto_sync_for_model(SlackUser)
enable_auto_sync_for_model(SlackChannel)

__all__ = [
    'SlackBase',
    'SlackUser',
    'SlackChannel'
] 