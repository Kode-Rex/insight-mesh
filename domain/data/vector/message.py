"""
Vector database data object for Message.
"""

from typing import Dict, Any, List, Optional, Tuple
from .base import ElasticsearchVectorBase


class VectorMessage(ElasticsearchVectorBase):
    """Vector database-specific message data object."""
    
    def __init__(self, vector_id: str, embedding: List[float] = None, metadata: Dict[str, Any] = None, content: str = None):
        super().__init__(vector_id, embedding, metadata, content)
        self.user_id = self.metadata.get('user_id', '')
        self.channel_id = self.metadata.get('channel_id', '')
        self.platform = self.metadata.get('platform', 'unknown')
    
    def find_similar_messages(self, top_k: int = 10, threshold: float = 0.7, same_channel: bool = False) -> List[Tuple['VectorMessage', float]]:
        """Find semantically similar messages."""
        filters = {}
        if same_channel and self.channel_id:
            filters['metadata.channel_id'] = self.channel_id
        
        return self.find_similar(top_k, threshold, filters, "message_vectors") 