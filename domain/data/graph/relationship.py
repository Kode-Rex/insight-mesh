"""
Neo4j graph relationship data object.
"""

from typing import Dict, Any, List, Optional
from .base import GraphBase
import logging

logger = logging.getLogger(__name__)


class GraphRelationship:
    """Neo4j-specific relationship data object."""
    
    def __init__(self, 
                 relationship_data: Dict[str, Any],
                 source_node: Dict[str, Any] = None,
                 target_node: Dict[str, Any] = None):
        """Initialize GraphRelationship from Neo4j relationship data."""
        self.type = relationship_data.get('type', '')
        self.properties = relationship_data.get('properties', {})
        self.source_node = source_node
        self.target_node = target_node
        
        # Common relationship properties
        self.strength = self.properties.get('strength', 1.0)
        self.created_at = self.properties.get('created_at')
        self.updated_at = self.properties.get('updated_at')
        self.context = self.properties.get('context', '')
    
    @classmethod
    def create_relationship(cls, 
                          source_id: str, 
                          target_id: str, 
                          relationship_type: str,
                          properties: Dict[str, Any] = None) -> bool:
        """Create a new relationship between two nodes."""
        try:
            # Use GraphBase to get driver
            base = GraphBase({})
            
            query = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            CREATE (a)-[r:{relationship_type}]->(b)
            """
            
            if properties:
                prop_string = ", ".join([f"r.{k} = ${k}" for k in properties.keys()])
                query += f" SET {prop_string}"
            
            query += " RETURN r"
            
            params = {
                "source_id": source_id,
                "target_id": target_id,
                **properties or {}
            }
            
            base.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
    
    @classmethod
    def get_relationships_between(cls, 
                                source_id: str, 
                                target_id: str) -> List['GraphRelationship']:
        """Get all relationships between two nodes."""
        try:
            base = GraphBase({})
            
            query = """
            MATCH (a {id: $source_id})-[r]-(b {id: $target_id})
            RETURN r, a, b, type(r) as rel_type
            """
            
            results = base.execute_query(query, {
                "source_id": source_id,
                "target_id": target_id
            })
            
            relationships = []
            for result in results:
                rel_data = {
                    'type': result['rel_type'],
                    'properties': dict(result['r'])
                }
                relationships.append(cls(rel_data, result['a'], result['b']))
            
            return relationships
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []
    
    @classmethod
    def get_strongest_connections(cls, 
                                node_id: str, 
                                relationship_types: List[str] = None,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Get the strongest connections for a node."""
        try:
            base = GraphBase({})
            
            type_filter = ""
            if relationship_types:
                type_filter = f":{':'.join(relationship_types)}"
            
            query = f"""
            MATCH (n {{id: $node_id}})-[r{type_filter}]-(connected)
            RETURN connected, r, type(r) as rel_type,
                   COALESCE(r.strength, 1.0) as strength
            ORDER BY strength DESC
            LIMIT $limit
            """
            
            return base.execute_query(query, {
                "node_id": node_id,
                "limit": limit
            })
        except Exception as e:
            logger.error(f"Error getting strongest connections: {e}")
            return []
    
    def update_strength(self, new_strength: float) -> bool:
        """Update the strength of this relationship."""
        if not self.source_node or not self.target_node:
            return False
        
        try:
            base = GraphBase({})
            
            query = f"""
            MATCH (a {{id: $source_id}})-[r:{self.type}]-(b {{id: $target_id}})
            SET r.strength = $strength, r.updated_at = datetime()
            RETURN r
            """
            
            base.execute_query(query, {
                "source_id": self.source_node.get('id'),
                "target_id": self.target_node.get('id'),
                "strength": new_strength
            })
            
            self.strength = new_strength
            return True
        except Exception as e:
            logger.error(f"Error updating relationship strength: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete this relationship."""
        if not self.source_node or not self.target_node:
            return False
        
        try:
            base = GraphBase({})
            
            query = f"""
            MATCH (a {{id: $source_id}})-[r:{self.type}]-(b {{id: $target_id}})
            DELETE r
            """
            
            base.execute_query(query, {
                "source_id": self.source_node.get('id'),
                "target_id": self.target_node.get('id')
            })
            
            return True
        except Exception as e:
            logger.error(f"Error deleting relationship: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "type": self.type,
            "properties": self.properties,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "strength": self.strength,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context
        } 