"""
Elasticsearch search data object for Channel.
"""

from typing import Dict, Any, List, Optional
from .base import SearchBase


class SearchChannel(SearchBase):
    """Elasticsearch-specific channel data object."""
    
    def __init__(self, doc_data: Dict[str, Any], index_name: str = "channels"):
        super().__init__(doc_data, index_name)
        self.name = self.source.get('name', '')
        self.topic = self.source.get('topic', '')
        self.member_count = self.source.get('member_count', 0)
        self.is_private = self.source.get('is_private', False)
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "topic": self.topic,
            "member_count": self.member_count,
            "is_private": self.is_private,
            "content": f"{self.name} {self.topic}",
            "meta": self.metadata
        } 