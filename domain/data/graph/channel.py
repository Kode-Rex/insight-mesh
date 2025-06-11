"""
Neo4j graph data object for Channel.
"""

from typing import Dict, Any, List, Optional
from .base import GraphBase
import logging

logger = logging.getLogger(__name__)


class GraphChannel(GraphBase):
    """Neo4j-specific channel data object."""
    
    def __init__(self, node_data: Dict[str, Any], labels: List[str] = None):
        """Initialize GraphChannel from Neo4j node data."""
        super().__init__(node_data, labels or ["Channel"])
        
        # Channel-specific properties
        self.name = self.properties.get('name', '')
        self.topic = self.properties.get('topic', '')
        self.purpose = self.properties.get('purpose', '')
        self.is_private = self.properties.get('is_private', False)
        self.member_count = self.properties.get('member_count', 0)
        self.platform = self.properties.get('platform', 'unknown')
    
    def save(self) -> bool:
        """Save channel node to Neo4j."""
        try:
            query = """
            MERGE (c:Channel {id: $id})
            SET c.name = $name,
                c.topic = $topic,
                c.purpose = $purpose,
                c.is_private = $is_private,
                c.member_count = $member_count,
                c.platform = $platform,
                c.updated_at = datetime()
            RETURN c
            """
            
            params = {
                "id": self.id,
                "name": self.name,
                "topic": self.topic,
                "purpose": self.purpose,
                "is_private": self.is_private,
                "member_count": self.member_count,
                "platform": self.platform
            }
            
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error saving channel: {e}")
            return False
    
    def get_members(self) -> List[Dict[str, Any]]:
        """Get all members of this channel."""
        query = """
        MATCH (c:Channel {id: $id})-[:MEMBER_OF]-(p:Person)
        RETURN p, 
               size((p)-[:SENT]-(:Message)-[:IN_CHANNEL]-(c)) as message_count
        ORDER BY message_count DESC
        """
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting channel members: {e}")
            return []
    
    def get_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get channel activity statistics."""
        query = """
        MATCH (c:Channel {id: $id})
        OPTIONAL MATCH (c)-[:IN_CHANNEL]-(m:Message)
        WHERE m.timestamp >= datetime() - duration({days: $days})
        RETURN 
            count(m) as message_count,
            count(DISTINCT m.user_id) as active_users,
            min(m.timestamp) as first_message,
            max(m.timestamp) as last_message
        """
        
        try:
            results = self.execute_query(query, {"id": self.id, "days": days})
            return results[0] if results else {}
        except Exception as e:
            logger.error(f"Error getting channel activity stats: {e}")
            return {} 