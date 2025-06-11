"""
Neo4j graph data object for Message.
"""

from typing import Dict, Any, List, Optional
from .base import GraphBase
import logging

logger = logging.getLogger(__name__)


class GraphMessage(GraphBase):
    """Neo4j-specific message data object."""
    
    def __init__(self, node_data: Dict[str, Any], labels: List[str] = None):
        """Initialize GraphMessage from Neo4j node data."""
        super().__init__(node_data, labels or ["Message"])
        
        # Message-specific properties
        self.content = self.properties.get('content', '')
        self.user_id = self.properties.get('user_id')
        self.channel_id = self.properties.get('channel_id')
        self.timestamp = self.properties.get('timestamp')
        self.thread_id = self.properties.get('thread_id')
        self.platform = self.properties.get('platform', 'unknown')
    
    def save(self) -> bool:
        """Save message node to Neo4j."""
        try:
            query = """
            MERGE (m:Message {id: $id})
            SET m.content = $content,
                m.user_id = $user_id,
                m.channel_id = $channel_id,
                m.timestamp = $timestamp,
                m.thread_id = $thread_id,
                m.platform = $platform,
                m.updated_at = datetime()
            RETURN m
            """
            
            params = {
                "id": self.id,
                "content": self.content,
                "user_id": self.user_id,
                "channel_id": self.channel_id,
                "timestamp": self.timestamp,
                "thread_id": self.thread_id,
                "platform": self.platform
            }
            
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
    
    def get_conversation_thread(self) -> List[Dict[str, Any]]:
        """Get all messages in the same conversation thread."""
        if not self.thread_id:
            return []
        
        query = """
        MATCH (m:Message {thread_id: $thread_id})
        RETURN m
        ORDER BY m.timestamp ASC
        """
        
        try:
            return self.execute_query(query, {"thread_id": self.thread_id})
        except Exception as e:
            logger.error(f"Error getting conversation thread: {e}")
            return []
    
    def get_related_messages(self, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get messages with similar content or from same context."""
        query = """
        MATCH (m:Message {id: $id})-[:IN_CHANNEL]-(c:Channel)-[:IN_CHANNEL]-(related:Message)
        WHERE related.id <> $id
        AND related.timestamp >= $id.timestamp - duration({hours: 24})
        AND related.timestamp <= $id.timestamp + duration({hours: 24})
        RETURN related, 
               CASE WHEN related.user_id = m.user_id THEN 0.8 ELSE 0.5 END as relevance_score
        ORDER BY relevance_score DESC, related.timestamp DESC
        LIMIT 10
        """
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting related messages: {e}")
            return [] 