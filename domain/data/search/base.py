"""
Base class for Elasticsearch search data objects.
"""

import os
from typing import Dict, Any, List, Optional, Union
from elasticsearch import Elasticsearch
import logging
import hashlib

logger = logging.getLogger(__name__)


class SearchBase:
    """Base class for all Elasticsearch search data objects."""
    
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get Elasticsearch client instance (singleton pattern)."""
        if cls._client is None:
            cls._client = Elasticsearch(
                [
                    {
                        "scheme": "http",
                        "host": os.getenv("ELASTICSEARCH_HOST", "localhost"),
                        "port": int(os.getenv("ELASTICSEARCH_PORT", "9200")),
                    }
                ]
            )
        return cls._client
    
    @classmethod
    def close_client(cls):
        """Close Elasticsearch client connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
    
    def __init__(self, doc_data: Dict[str, Any], index_name: str = None):
        """
        Initialize search data object from Elasticsearch document data.
        
        Args:
            doc_data: Dictionary containing document data from Elasticsearch
            index_name: Name of the Elasticsearch index
        """
        self.id = doc_data.get('_id') or doc_data.get('id')
        self.source = doc_data.get('_source', doc_data)
        self.score = doc_data.get('_score')
        self.index = doc_data.get('_index', index_name)
        self.doc_type = doc_data.get('_type')
        self.version = doc_data.get('_version')
        
        # Extract common fields
        self.content = self.source.get('content', '')
        self.title = self.source.get('title', '')
        self.metadata = self.source.get('meta', {})
        self.timestamp = self.source.get('timestamp')
        self.created_at = self.source.get('created_at')
        self.updated_at = self.source.get('updated_at')
    
    def generate_document_id(self, source_type: str, identifier: str) -> str:
        """Generate a consistent document ID for Elasticsearch."""
        return hashlib.md5(f"{source_type}:{identifier}".encode()).hexdigest()
    
    def index_document(self, index: str, doc_id: str = None, document: Dict[str, Any] = None) -> Dict[str, Any]:
        """Index a document in Elasticsearch."""
        try:
            doc_id = doc_id or self.id
            document = document or self.to_elasticsearch_doc()
            
            result = self.get_client().index(
                index=index,
                id=doc_id,
                document=document
            )
            
            logger.info(f"Indexed document {doc_id} in index {index}")
            return result
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise
    
    def update_document(self, index: str, doc_id: str = None, partial_doc: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update a document in Elasticsearch."""
        try:
            doc_id = doc_id or self.id
            partial_doc = partial_doc or self.to_elasticsearch_doc()
            
            result = self.get_client().update(
                index=index,
                id=doc_id,
                doc=partial_doc
            )
            
            logger.info(f"Updated document {doc_id} in index {index}")
            return result
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def delete_document(self, index: str, doc_id: str = None) -> Dict[str, Any]:
        """Delete a document from Elasticsearch."""
        try:
            doc_id = doc_id or self.id
            
            result = self.get_client().delete(
                index=index,
                id=doc_id
            )
            
            logger.info(f"Deleted document {doc_id} from index {index}")
            return result
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    def search(self, 
               query: Union[str, Dict[str, Any]], 
               index: str = None,
               size: int = 10,
               from_: int = 0,
               sort: List[Dict[str, Any]] = None,
               filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a search query."""
        try:
            index = index or self.index
            
            # Build query body
            if isinstance(query, str):
                # Simple text query
                query_body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^2", "title^3", "name^2"]
                        }
                    },
                    "size": size,
                    "from": from_
                }
            else:
                # Complex query object
                query_body = query
                query_body.update({
                    "size": size,
                    "from": from_
                })
            
            # Add sorting
            if sort:
                query_body["sort"] = sort
            
            # Add filters
            if filters:
                if "query" not in query_body:
                    query_body["query"] = {"match_all": {}}
                
                query_body["query"] = {
                    "bool": {
                        "must": query_body["query"],
                        "filter": [{"term": {k: v}} for k, v in filters.items()]
                    }
                }
            
            result = self.get_client().search(
                index=index,
                body=query_body
            )
            
            logger.info(f"Search executed on index {index}, found {result['hits']['total']['value']} results")
            return result
        except Exception as e:
            logger.error(f"Error executing search: {e}")
            raise
    
    def get_document(self, index: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        try:
            result = self.get_client().get(
                index=index,
                id=doc_id
            )
            return result
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def bulk_index(self, documents: List[Dict[str, Any]], index: str) -> Dict[str, Any]:
        """Bulk index multiple documents."""
        try:
            actions = []
            for doc in documents:
                action = {
                    "_index": index,
                    "_id": doc.get("id") or self.generate_document_id("bulk", str(hash(str(doc)))),
                    "_source": doc
                }
                actions.append(action)
            
            result = self.get_client().bulk(body=actions)
            logger.info(f"Bulk indexed {len(documents)} documents to index {index}")
            return result
        except Exception as e:
            logger.error(f"Error bulk indexing documents: {e}")
            raise
    
    def create_index(self, index: str, mappings: Dict[str, Any] = None, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create an index with mappings and settings."""
        try:
            body = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings
            
            result = self.get_client().indices.create(
                index=index,
                body=body
            )
            
            logger.info(f"Created index {index}")
            return result
        except Exception as e:
            logger.error(f"Error creating index {index}: {e}")
            raise
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        """Convert object to Elasticsearch document format. Should be implemented by subclasses."""
        return {
            "id": self.id,
            "content": self.content,
            "title": self.title,
            "meta": self.metadata,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search object to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "score": self.score,
            "index": self.index,
            "content": self.content,
            "title": self.title,
            "metadata": self.metadata
        } 