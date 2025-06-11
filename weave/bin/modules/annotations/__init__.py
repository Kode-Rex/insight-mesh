"""
Weave multi-store annotations for SQLAlchemy models.

This module provides decorators and mixins to add Neo4j graph and Elasticsearch
search capabilities to existing SQLAlchemy models without duplicating the schema.

Part of the Weave CLI infrastructure - will be extracted as standalone when Weave
becomes its own library.
"""

from .graph import neo4j_node, neo4j_relationship, GraphMixin
from .search import elasticsearch_index, SearchMixin
from .sync import SyncMixin

__all__ = [
    'neo4j_node',
    'neo4j_relationship', 
    'GraphMixin',
    'elasticsearch_index',
    'SearchMixin',
    'SyncMixin'
] 