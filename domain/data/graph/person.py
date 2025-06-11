"""
Neo4j graph data object for Person.
"""

from typing import Dict, Any, List, Optional
from .base import GraphBase
import logging

logger = logging.getLogger(__name__)


class GraphPerson(GraphBase):
    """Neo4j-specific person data object."""
    
    def __init__(self, node_data: Dict[str, Any], labels: List[str] = None):
        """Initialize GraphPerson from Neo4j node data."""
        super().__init__(node_data, labels or ["Person"])
        
        # Person-specific properties
        self.name = self.properties.get('name')
        self.email = self.properties.get('email')
        self.display_name = self.properties.get('display_name')
        self.title = self.properties.get('title')
        self.department = self.properties.get('department')
    
    @classmethod
    def find_by_id(cls, person_id: str) -> Optional['GraphPerson']:
        """Find person by ID in Neo4j."""
        instance = cls({})  # Temporary instance to access execute_query
        query = """
        MATCH (p:Person {id: $id})
        RETURN p, labels(p) as labels
        """
        
        try:
            results = instance.execute_query(query, {"id": person_id})
            if results:
                result = results[0]
                return cls(result['p'], result['labels'])
            return None
        except Exception as e:
            logger.error(f"Error finding person by ID: {e}")
            return None
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional['GraphPerson']:
        """Find person by email in Neo4j."""
        instance = cls({})
        query = """
        MATCH (p:Person {email: $email})
        RETURN p, labels(p) as labels
        """
        
        try:
            results = instance.execute_query(query, {"email": email})
            if results:
                result = results[0]
                return cls(result['p'], result['labels'])
            return None
        except Exception as e:
            logger.error(f"Error finding person by email: {e}")
            return None
    
    def save(self) -> bool:
        """Save person node to Neo4j."""
        try:
            query = """
            MERGE (p:Person {id: $id})
            SET p.name = $name,
                p.email = $email,
                p.display_name = $display_name,
                p.title = $title,
                p.department = $department,
                p.updated_at = datetime()
            RETURN p
            """
            
            params = {
                "id": self.id,
                "name": self.name,
                "email": self.email,
                "display_name": self.display_name,
                "title": self.title,
                "department": self.department
            }
            
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error saving person: {e}")
            return False
    
    def get_colleagues(self, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Get colleagues through shared channels or projects."""
        query = """
        MATCH (p:Person {id: $id})-[:MEMBER_OF|WORKS_ON*1..%d]-(shared)-[:MEMBER_OF|WORKS_ON*1..%d]-(colleague:Person)
        WHERE colleague.id <> $id
        RETURN DISTINCT colleague, 
               count(shared) as connection_strength,
               collect(DISTINCT labels(shared)) as shared_contexts
        ORDER BY connection_strength DESC
        LIMIT 20
        """ % (max_depth, max_depth)
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting colleagues: {e}")
            return []
    
    def get_communication_network(self) -> List[Dict[str, Any]]:
        """Get people this person communicates with most."""
        query = """
        MATCH (p:Person {id: $id})-[:SENT|RECEIVED]-(m:Message)-[:SENT|RECEIVED]-(other:Person)
        WHERE other.id <> $id
        RETURN other,
               count(m) as message_count,
               max(m.timestamp) as last_communication
        ORDER BY message_count DESC
        LIMIT 15
        """
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting communication network: {e}")
            return []
    
    def get_expertise_areas(self) -> List[Dict[str, Any]]:
        """Get areas of expertise based on message content and channels."""
        query = """
        MATCH (p:Person {id: $id})-[:SENT]-(m:Message)-[:IN_CHANNEL]-(c:Channel)
        RETURN c.name as channel,
               c.topic as topic,
               count(m) as message_count,
               collect(DISTINCT c.tags) as tags
        ORDER BY message_count DESC
        LIMIT 10
        """
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting expertise areas: {e}")
            return []
    
    def get_influence_score(self) -> Dict[str, Any]:
        """Calculate influence score based on network position."""
        query = """
        MATCH (p:Person {id: $id})
        OPTIONAL MATCH (p)-[:SENT]-(m:Message)
        OPTIONAL MATCH (p)-[:MEMBER_OF]-(c:Channel)
        OPTIONAL MATCH (p)-[r:REPORTS_TO|MANAGES]-(other:Person)
        RETURN 
            count(DISTINCT m) as messages_sent,
            count(DISTINCT c) as channels_joined,
            count(DISTINCT other) as direct_reports_or_managers,
            size((p)-[:SENT]-(:Message)-[:RECEIVED]-(other:Person)) as unique_contacts
        """
        
        try:
            results = self.execute_query(query, {"id": self.id})
            if results:
                return results[0]
            return {}
        except Exception as e:
            logger.error(f"Error calculating influence score: {e}")
            return {}
    
    def find_similar_people(self, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find people with similar roles, departments, or communication patterns."""
        query = """
        MATCH (p:Person {id: $id})
        MATCH (other:Person)
        WHERE other.id <> $id
        WITH p, other,
             CASE WHEN p.department = other.department THEN 0.3 ELSE 0 END +
             CASE WHEN p.title = other.title THEN 0.4 ELSE 0 END +
             CASE WHEN size((p)-[:MEMBER_OF]-(:Channel)-[:MEMBER_OF]-(other)) > 0 THEN 0.3 ELSE 0 END
             as similarity_score
        WHERE similarity_score >= $threshold
        RETURN other, similarity_score
        ORDER BY similarity_score DESC
        LIMIT 10
        """
        
        try:
            return self.execute_query(query, {
                "id": self.id,
                "threshold": similarity_threshold
            })
        except Exception as e:
            logger.error(f"Error finding similar people: {e}")
            return []
    
    def get_activity_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get person's activity timeline over specified days."""
        query = """
        MATCH (p:Person {id: $id})-[:SENT]-(m:Message)
        WHERE m.timestamp >= datetime() - duration({days: $days})
        RETURN date(m.timestamp) as date,
               count(m) as message_count,
               collect(DISTINCT m.channel_id) as active_channels
        ORDER BY date DESC
        """
        
        try:
            return self.execute_query(query, {
                "id": self.id,
                "days": days
            })
        except Exception as e:
            logger.error(f"Error getting activity timeline: {e}")
            return []
    
    def create_works_with_relationship(self, other_person_id: str, strength: float = 1.0, context: str = None) -> bool:
        """Create a WORKS_WITH relationship with another person."""
        properties = {
            "strength": strength,
            "created_at": "datetime()"
        }
        if context:
            properties["context"] = context
        
        return self.create_relationship(other_person_id, "WORKS_WITH", properties)
    
    def create_reports_to_relationship(self, manager_id: str) -> bool:
        """Create a REPORTS_TO relationship with a manager."""
        return self.create_relationship(manager_id, "REPORTS_TO", {
            "created_at": "datetime()"
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert GraphPerson to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            "name": self.name,
            "email": self.email,
            "display_name": self.display_name,
            "title": self.title,
            "department": self.department
        })
        return base_dict 