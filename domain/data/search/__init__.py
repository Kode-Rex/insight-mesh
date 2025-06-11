"""
Search database domain models package.
Contains Elasticsearch-specific data objects.
"""

from .base import SearchBase
from .person import SearchPerson
from .message import SearchMessage
from .channel import SearchChannel
from .document import SearchDocument

__all__ = [
    'SearchBase',
    'SearchPerson',
    'SearchMessage',
    'SearchChannel', 
    'SearchDocument'
] 