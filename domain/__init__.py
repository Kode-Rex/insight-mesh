"""
Domain models for the Insight Mesh project.
Contains all shared database models used across services.
"""

# Import all InsightMesh models
from .insightmesh import (
    InsightMeshBase,
    InsightMeshUser,
    Context,
    Conversation,
    Message
)

# Import all Slack models  
from .slack import (
    SlackBase,
    SlackUser,
    SlackChannel
)

__all__ = [
    # InsightMesh models
    'InsightMeshBase',
    'InsightMeshUser',
    'Context', 
    'Conversation',
    'Message',
    # Slack models
    'SlackBase',
    'SlackUser',
    'SlackChannel'
] 