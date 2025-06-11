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

# Import all Graph models (Neo4j)
from .graph import (
    GraphBase,
    GraphPerson,
    GraphMessage,
    GraphChannel,
    GraphRelationship
)

# Import all Search models (Elasticsearch)
from .search import (
    SearchBase,
    SearchPerson,
    SearchMessage,
    SearchChannel,
    SearchDocument
)

# Import all Vector models
from .vector import (
    VectorBase,
    VectorPerson,
    VectorMessage,
    VectorDocument
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
    'SlackChannel',
    # Graph models (Neo4j)
    'GraphBase',
    'GraphPerson',
    'GraphMessage',
    'GraphChannel',
    'GraphRelationship',
    # Search models (Elasticsearch)
    'SearchBase',
    'SearchPerson',
    'SearchMessage',
    'SearchChannel',
    'SearchDocument',
    # Vector models
    'VectorBase',
    'VectorPerson',
    'VectorMessage',
    'VectorDocument'
] 