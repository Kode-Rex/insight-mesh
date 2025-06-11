"""
Base class for Neo4j graph data objects.
"""

import os
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class GraphBase:
    """Base class for all Neo4j graph data objects."""
    
    _driver = None
    
    @classmethod
    def get_driver(cls):
        """Get Neo4j driver instance (singleton pattern)."""
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                auth=(
                    os.getenv("NEO4J_USER", "neo4j"), 
                    os.getenv("NEO4J_PASSWORD", "password")
                )
            )
        return cls._driver
    
    @classmethod
    def close_driver(cls):
        """Close Neo4j driver connection."""
        if cls._driver:
            cls._driver.close()
            cls._driver = None
    
    def __init__(self, node_data: Dict[str, Any], labels: List[str] = None):
        """
        Initialize graph data object from Neo4j node data.
        
        Args:
            node_data: Dictionary containing node properties
            labels: List of node labels
        """
        self.id = node_data.get('id')
        self.properties = node_data
        self.labels = labels or []
        self._relationships = {}
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Neo4j query and return results."""
        try:
            with self.get_driver().session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing Neo4j query: {e}")
            raise
    
    def save(self) -> bool:
        """Save node to Neo4j. Should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement save method")
    
    def delete(self) -> bool:
        """Delete node from Neo4j."""
        try:
            query = """
            MATCH (n {id: $id})
            DETACH DELETE n
            """
            self.execute_query(query, {"id": self.id})
            return True
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return False
    
    def get_relationships(self, relationship_type: str = None, direction: str = "both") -> List[Dict[str, Any]]:
        """
        Get relationships for this node.
        
        Args:
            relationship_type: Filter by relationship type (optional)
            direction: 'incoming', 'outgoing', or 'both'
        """
        direction_map = {
            "outgoing": "->",
            "incoming": "<-",
            "both": "-"
        }
        
        rel_pattern = f"-[r{':' + relationship_type if relationship_type else ''}]-"
        if direction != "both":
            rel_pattern = direction_map[direction] + rel_pattern[1:]
            if direction == "outgoing":
                rel_pattern = rel_pattern + "->"
            else:
                rel_pattern = "<-" + rel_pattern[2:]
        
        query = f"""
        MATCH (n {{id: $id}}){rel_pattern}(m)
        RETURN r, m, labels(m) as target_labels
        """
        
        try:
            return self.execute_query(query, {"id": self.id})
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []
    
    def create_relationship(self, target_node_id: str, relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """Create a relationship to another node."""
        try:
            query = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            CREATE (a)-[r:{relationship_type}]->(b)
            """
            
            if properties:
                prop_string = ", ".join([f"r.{k} = ${k}" for k in properties.keys()])
                query += f" SET {prop_string}"
            
            query += " RETURN r"
            
            params = {
                "source_id": self.id,
                "target_id": target_node_id,
                **properties or {}
            }
            
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph object to dictionary."""
        return {
            "id": self.id,
            "labels": self.labels,
            "properties": self.properties
        } 