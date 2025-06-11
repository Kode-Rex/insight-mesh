"""
Vector database data object for Document.
"""

from typing import Dict, Any, List, Optional, Tuple
from .base import ElasticsearchVectorBase


class VectorDocument(ElasticsearchVectorBase):
    """Vector database-specific document data object."""
    
    def __init__(self, vector_id: str, embedding: List[float] = None, metadata: Dict[str, Any] = None, content: str = None):
        super().__init__(vector_id, embedding, metadata, content)
        self.document_type = self.metadata.get('document_type', 'unknown')
        self.author = self.metadata.get('author', '')
        self.file_name = self.metadata.get('file_name', '')
    
    def find_similar_documents(self, top_k: int = 10, threshold: float = 0.7, same_type: bool = False) -> List[Tuple['VectorDocument', float]]:
        """Find semantically similar documents."""
        filters = {}
        if same_type and self.document_type:
            filters['metadata.document_type'] = self.document_type
        
        return self.find_similar(top_k, threshold, filters, "document_vectors") 