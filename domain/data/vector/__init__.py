"""
Vector database domain models package.
Contains vector database-specific data objects for embeddings and similarity search.
"""

from .base import VectorBase
from .person import VectorPerson
from .message import VectorMessage
from .document import VectorDocument

__all__ = [
    'VectorBase',
    'VectorPerson',
    'VectorMessage',
    'VectorDocument'
] 