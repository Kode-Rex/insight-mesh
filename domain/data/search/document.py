"""
Elasticsearch search data object for Document.
"""

from typing import Dict, Any, List, Optional
from .base import SearchBase


class SearchDocument(SearchBase):
    """Elasticsearch-specific document data object."""
    
    def __init__(self, doc_data: Dict[str, Any], index_name: str = "documents"):
        super().__init__(doc_data, index_name)
        self.file_name = self.source.get('file_name', '')
        self.file_type = self.source.get('file_type', '')
        self.author = self.source.get('author', '')
        self.url = self.source.get('url', '')
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "title": self.title,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "author": self.author,
            "url": self.url,
            "meta": self.metadata
        } 