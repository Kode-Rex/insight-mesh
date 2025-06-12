"""
Elasticsearch search annotations for SQLAlchemy models.
"""

import functools
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass
from elasticsearch import Elasticsearch
import os
import json


@dataclass
class ElasticsearchIndexConfig:
    """Configuration for Elasticsearch index mapping."""
    index_name: str
    doc_type: str = '_doc'
    properties: Optional[List[str]] = None  # If None, use all SQLAlchemy columns
    id_field: str = 'id'
    exclude_fields: Optional[List[str]] = None
    text_fields: Optional[List[str]] = None  # Fields to analyze for full-text search
    mapping: Optional[Dict[str, Any]] = None  # Custom Elasticsearch mapping


def elasticsearch_index(index_name: str,
                       doc_type: str = '_doc',
                       properties: Optional[List[str]] = None,
                       id_field: str = 'id',
                       exclude_fields: Optional[List[str]] = None,
                       text_fields: Optional[List[str]] = None,
                       mapping: Optional[Dict[str, Any]] = None):
    """
    Decorator to mark a SQLAlchemy model for Elasticsearch indexing.
    
    Args:
        index_name: Elasticsearch index name
        doc_type: Document type (usually '_doc' for modern ES)
        properties: List of SQLAlchemy column names to index (None = all)
        id_field: Primary key field name
        exclude_fields: Fields to exclude from indexing
        text_fields: Fields to treat as full-text searchable
        mapping: Custom Elasticsearch mapping
    """
    def decorator(cls):
        config = ElasticsearchIndexConfig(
            index_name=index_name,
            doc_type=doc_type,
            properties=properties,
            id_field=id_field,
            exclude_fields=exclude_fields or [],
            text_fields=text_fields or [],
            mapping=mapping
        )
        cls._elasticsearch_config = config
        
        # Add SearchMixin methods if not already present
        if not hasattr(cls, 'sync_to_elasticsearch'):
            # Dynamically add mixin methods
            for attr_name in dir(SearchMixin):
                if not attr_name.startswith('__'):  # Include _get_elasticsearch_document but not __init__ etc
                    attr_value = getattr(SearchMixin, attr_name)
                    if callable(attr_value):
                        setattr(cls, attr_name, attr_value)
        
        return cls
    return decorator


class SearchMixin:
    """Mixin to add Elasticsearch capabilities to SQLAlchemy models."""
    
    @classmethod
    def get_elasticsearch_client(cls):
        """Get Elasticsearch client instance."""
        if not hasattr(cls, '_elasticsearch_client'):
            es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
            es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
            es_scheme = os.getenv("ELASTICSEARCH_SCHEME", "http")
            
            cls._elasticsearch_client = Elasticsearch(
                [f"{es_scheme}://{es_host}:{es_port}"],
                # Add auth if needed
                # http_auth=(username, password),
            )
        return cls._elasticsearch_client
    
    def _get_elasticsearch_document(self) -> Dict[str, Any]:
        """Extract document for Elasticsearch from SQLAlchemy instance."""
        config = getattr(self.__class__, '_elasticsearch_config', None)
        if not config:
            return {}
        
        document = {}
        columns = self.__table__.columns.keys()
        
        # Determine which fields to include
        if config.properties:
            fields = config.properties
        else:
            fields = [col for col in columns if col not in config.exclude_fields]
        
        for field in fields:
            if hasattr(self, field):
                value = getattr(self, field)
                # Convert datetime to string for Elasticsearch
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                # Convert complex objects to JSON
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value) if not isinstance(value, str) else value
                # Skip None values
                if value is not None:
                    document[field] = value
        
        return document
    
    def sync_to_elasticsearch(self):
        """Sync this instance to Elasticsearch."""
        config = getattr(self.__class__, '_elasticsearch_config', None)
        if not config:
            raise ValueError(f"No Elasticsearch configuration found for {self.__class__.__name__}")
        
        client = self.get_elasticsearch_client()
        document = self._get_elasticsearch_document()
        doc_id = getattr(self, config.id_field)
        
        client.index(
            index=config.index_name,
            id=doc_id,
            body=document
        )
    
    def delete_from_elasticsearch(self):
        """Delete this instance from Elasticsearch."""
        config = getattr(self.__class__, '_elasticsearch_config', None)
        if not config:
            return
        
        client = self.get_elasticsearch_client()
        doc_id = getattr(self, config.id_field)
        
        try:
            client.delete(
                index=config.index_name,
                id=doc_id
            )
        except Exception:
            # Document might not exist, ignore
            pass
    
    @classmethod
    def search_elasticsearch(cls, query: str, **kwargs):
        """Search this model in Elasticsearch."""
        config = getattr(cls, '_elasticsearch_config', None)
        if not config:
            raise ValueError(f"No Elasticsearch configuration found for {cls.__name__}")
        
        client = cls.get_elasticsearch_client()
        
        # Build search query
        if config.text_fields:
            # Multi-field search on specified text fields
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": config.text_fields,
                        "type": "best_fields"
                    }
                }
            }
        else:
            # Simple query string search
            search_body = {
                "query": {
                    "query_string": {
                        "query": query
                    }
                }
            }
        
        # Add any additional search parameters
        search_body.update(kwargs)
        
        response = client.search(
            index=config.index_name,
            body=search_body
        )
        
        return response['hits']
    
    @classmethod
    def create_elasticsearch_index(cls):
        """Create the Elasticsearch index with proper mapping."""
        config = getattr(cls, '_elasticsearch_config', None)
        if not config:
            raise ValueError(f"No Elasticsearch configuration found for {cls.__name__}")
        
        client = cls.get_elasticsearch_client()
        
        # Use custom mapping if provided, otherwise create basic mapping
        if config.mapping:
            mapping = config.mapping
        else:
            mapping = cls._generate_elasticsearch_mapping()
        
        index_body = {
            "mappings": mapping
        }
        
        # Create index if it doesn't exist
        if not client.indices.exists(index=config.index_name):
            client.indices.create(
                index=config.index_name,
                body=index_body
            )
    
    @classmethod
    def _generate_elasticsearch_mapping(cls) -> Dict[str, Any]:
        """Generate basic Elasticsearch mapping from SQLAlchemy model."""
        config = getattr(cls, '_elasticsearch_config')
        mapping = {"properties": {}}
        
        # Get SQLAlchemy column types and create appropriate ES mappings
        for column in cls.__table__.columns:
            if column.name in config.exclude_fields:
                continue
            
            # Map SQLAlchemy types to Elasticsearch types
            if str(column.type).startswith('VARCHAR') or str(column.type).startswith('TEXT'):
                if column.name in config.text_fields:
                    mapping["properties"][column.name] = {
                        "type": "text",
                        "analyzer": "standard"
                    }
                else:
                    mapping["properties"][column.name] = {"type": "keyword"}
            elif str(column.type).startswith('INTEGER'):
                mapping["properties"][column.name] = {"type": "integer"}
            elif str(column.type).startswith('BOOLEAN'):
                mapping["properties"][column.name] = {"type": "boolean"}
            elif str(column.type).startswith('DATETIME'):
                mapping["properties"][column.name] = {"type": "date"}
            elif str(column.type).startswith('JSON'):
                mapping["properties"][column.name] = {"type": "object"}
            else:
                # Default to keyword for unknown types
                mapping["properties"][column.name] = {"type": "keyword"}
        
        return mapping 