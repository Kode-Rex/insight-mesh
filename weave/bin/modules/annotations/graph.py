"""
Neo4j graph annotations for SQLAlchemy models.
"""

import functools
from typing import Dict, Any, List, Optional, Callable, Type, Union
from dataclasses import dataclass
from neo4j import GraphDatabase
import os


@dataclass
class Neo4jNodeConfig:
    """Configuration for Neo4j node mapping."""
    label: str
    properties: Optional[List[str]] = None  # If None, use all SQLAlchemy columns
    id_field: str = 'id'
    exclude_fields: Optional[List[str]] = None


@dataclass 
class Neo4jRelationshipConfig:
    """Configuration for Neo4j relationship mapping."""
    type: str
    target_model: Union[Type, str]  # Can be class or string for forward references
    source_field: str
    target_field: str = 'id'
    properties: Optional[List[str]] = None


def neo4j_node(label: str, 
               properties: Optional[List[str]] = None,
               id_field: str = 'id',
               exclude_fields: Optional[List[str]] = None):
    """
    Decorator to mark a SQLAlchemy model as a Neo4j node.
    
    Args:
        label: Neo4j node label
        properties: List of SQLAlchemy column names to sync (None = all)
        id_field: Primary key field name
        exclude_fields: Fields to exclude from syncing
    """
    def decorator(cls):
        config = Neo4jNodeConfig(
            label=label,
            properties=properties,
            id_field=id_field,
            exclude_fields=exclude_fields or []
        )
        cls._neo4j_node_config = config
        
        # Add GraphMixin methods if not already present
        if not hasattr(cls, 'sync_to_neo4j'):
            # Dynamically add mixin methods
            for attr_name in dir(GraphMixin):
                if not attr_name.startswith('__'):  # Include _get_neo4j_properties but not __init__ etc
                    attr_value = getattr(GraphMixin, attr_name)
                    if callable(attr_value):
                        setattr(cls, attr_name, attr_value)
        
        return cls
    return decorator


def neo4j_relationship(type: str, 
                      target_model: Union[Type, str],
                      source_field: str,
                      target_field: str = 'id',
                      properties: Optional[List[str]] = None):
    """
    Decorator to define Neo4j relationships between models.
    
    Args:
        type: Relationship type in Neo4j
        target_model: Target SQLAlchemy model class or string name
        source_field: Field in source model that references target
        target_field: Field in target model (usually 'id')
        properties: Additional relationship properties
    """
    def decorator(cls):
        if not hasattr(cls, '_neo4j_relationships'):
            cls._neo4j_relationships = []
        
        config = Neo4jRelationshipConfig(
            type=type,
            target_model=target_model,
            source_field=source_field,
            target_field=target_field,
            properties=properties
        )
        cls._neo4j_relationships.append(config)
        return cls
    return decorator


class GraphMixin:
    """Mixin to add Neo4j capabilities to SQLAlchemy models."""
    
    @classmethod
    def get_neo4j_driver(cls):
        """Get Neo4j driver instance."""
        if not hasattr(cls, '_neo4j_driver'):
            cls._neo4j_driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                auth=(os.getenv("NEO4J_USER", "neo4j"), 
                      os.getenv("NEO4J_PASSWORD", "password"))
            )
        return cls._neo4j_driver
    
    def _get_neo4j_properties(self) -> Dict[str, Any]:
        """Extract properties for Neo4j from SQLAlchemy instance."""
        config = getattr(self.__class__, '_neo4j_node_config', None)
        if not config:
            return {}
        
        properties = {}
        columns = self.__table__.columns.keys()
        
        # Determine which fields to include
        if config.properties:
            fields = config.properties
        else:
            fields = [col for col in columns if col not in config.exclude_fields]
        
        for field in fields:
            if hasattr(self, field):
                value = getattr(self, field)
                # Convert datetime to string for Neo4j
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                # Skip None values
                if value is not None:
                    properties[field] = value
        
        return properties
    
    def sync_to_neo4j(self):
        """Sync this instance to Neo4j."""
        config = getattr(self.__class__, '_neo4j_node_config', None)
        if not config:
            raise ValueError(f"No Neo4j configuration found for {self.__class__.__name__}")
        
        driver = self.get_neo4j_driver()
        properties = self._get_neo4j_properties()
        node_id = getattr(self, config.id_field)
        
        with driver.session() as session:
            query = f"""
            MERGE (n:{config.label} {{{config.id_field}: $id}})
            SET n += $properties
            RETURN n
            """
            session.run(query, id=node_id, properties=properties)
    
    def _resolve_target_model(self, target_model_ref: Union[Type, str]) -> Optional[Type]:
        """Resolve target model from class or string reference."""
        if isinstance(target_model_ref, str):
            # Try to resolve from the same module first
            module = self.__class__.__module__
            if hasattr(__import__(module, fromlist=[target_model_ref]), target_model_ref):
                return getattr(__import__(module, fromlist=[target_model_ref]), target_model_ref)
            
            # Could add more sophisticated resolution logic here
            return None
        return target_model_ref
    
    def sync_relationships_to_neo4j(self):
        """Sync relationships to Neo4j."""
        relationships = getattr(self.__class__, '_neo4j_relationships', [])
        if not relationships:
            return
        
        driver = self.get_neo4j_driver()
        config = getattr(self.__class__, '_neo4j_node_config')
        source_id = getattr(self, config.id_field)
        
        with driver.session() as session:
            for rel_config in relationships:
                target_value = getattr(self, rel_config.source_field, None)
                if target_value is None:
                    continue
                
                # Resolve target model
                target_model = self._resolve_target_model(rel_config.target_model)
                if not target_model:
                    continue
                
                target_config = getattr(target_model, '_neo4j_node_config', None)
                if not target_config:
                    continue
                
                query = f"""
                MATCH (source:{config.label} {{{config.id_field}: $source_id}})
                MATCH (target:{target_config.label} {{{rel_config.target_field}: $target_id}})
                MERGE (source)-[r:{rel_config.type}]->(target)
                RETURN r
                """
                session.run(query, source_id=source_id, target_id=target_value)
    
    @classmethod
    def find_in_neo4j(cls, **filters):
        """Find nodes in Neo4j by properties."""
        config = getattr(cls, '_neo4j_node_config', None)
        if not config:
            raise ValueError(f"No Neo4j configuration found for {cls.__name__}")
        
        driver = cls.get_neo4j_driver()
        
        # Build WHERE clause
        where_parts = []
        params = {}
        for key, value in filters.items():
            where_parts.append(f"n.{key} = ${key}")
            params[key] = value
        
        where_clause = " AND ".join(where_parts) if where_parts else "true"
        
        with driver.session() as session:
            query = f"""
            MATCH (n:{config.label})
            WHERE {where_clause}
            RETURN n
            """
            result = session.run(query, **params)
            return [record["n"] for record in result] 