"""
Elasticsearch search data object for Message.
"""

from typing import Dict, Any, List, Optional
from .base import SearchBase
import logging

logger = logging.getLogger(__name__)


class SearchMessage(SearchBase):
    """Elasticsearch-specific message data object."""
    
    def __init__(self, doc_data: Dict[str, Any], index_name: str = "messages"):
        """Initialize SearchMessage from Elasticsearch document data."""
        super().__init__(doc_data, index_name)
        
        # Message-specific fields
        self.user_id = self.source.get('user_id', '')
        self.channel_id = self.source.get('channel_id', '')
        self.thread_id = self.source.get('thread_id')
        self.platform = self.source.get('platform', 'unknown')
        self.message_type = self.source.get('message_type', 'text')
        
        # Content analysis fields
        self.sentiment = self.source.get('sentiment')
        self.topics = self.source.get('topics', [])
        self.mentions = self.source.get('mentions', [])
        self.attachments = self.source.get('attachments', [])
    
    def search_by_content(self, query: str, fuzzy: bool = True) -> Dict[str, Any]:
        """Search messages by content with highlighting."""
        search_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "title"],
                    "fuzziness": "AUTO" if fuzzy else 0
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    }
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ]
        }
        
        return self.search(search_query, index=self.index)
    
    def search_by_user(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Search messages by specific user within time range."""
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": user_id}},
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{days}d"
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "aggs": {
                "channels": {
                    "terms": {"field": "channel_id", "size": 10}
                },
                "daily_activity": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "day"
                    }
                }
            }
        }
        
        return self.search(search_query, index=self.index)
    
    def search_conversation_thread(self, thread_id: str) -> Dict[str, Any]:
        """Get all messages in a conversation thread."""
        search_query = {
            "query": {
                "term": {"thread_id": thread_id}
            },
            "sort": [{"timestamp": {"order": "asc"}}],
            "size": 100
        }
        
        return self.search(search_query, index=self.index)
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        """Convert SearchMessage to Elasticsearch document format."""
        return {
            "content": self.content,
            "title": self.title,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "thread_id": self.thread_id,
            "platform": self.platform,
            "message_type": self.message_type,
            "sentiment": self.sentiment,
            "topics": self.topics,
            "mentions": self.mentions,
            "attachments": self.attachments,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.metadata
        } 