"""
Base class for vector database data objects.
"""

import os
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class VectorBase(ABC):
    """Base class for all vector database data objects."""
    
    def __init__(self, 
                 vector_id: str,
                 embedding: Union[List[float], np.ndarray] = None,
                 metadata: Dict[str, Any] = None,
                 content: str = None):
        """
        Initialize vector data object.
        
        Args:
            vector_id: Unique identifier for the vector
            embedding: Vector embedding (list of floats or numpy array)
            metadata: Associated metadata
            content: Original content that was embedded
        """
        self.id = vector_id
        self.embedding = np.array(embedding) if embedding is not None else None
        self.metadata = metadata or {}
        self.content = content
        self.dimension = len(embedding) if embedding else None
        
        # Common metadata fields
        self.source = self.metadata.get('source')
        self.source_id = self.metadata.get('source_id')
        self.timestamp = self.metadata.get('timestamp')
        self.created_at = self.metadata.get('created_at')
    
    @abstractmethod
    def get_client(self):
        """Get vector database client. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """Save vector to database. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def delete(self) -> bool:
        """Delete vector from database. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def find_similar(self, 
                    top_k: int = 10, 
                    threshold: float = 0.7,
                    filters: Dict[str, Any] = None) -> List[Tuple['VectorBase', float]]:
        """Find similar vectors. Must be implemented by subclasses."""
        pass
    
    def cosine_similarity(self, other_embedding: Union[List[float], np.ndarray]) -> float:
        """Calculate cosine similarity between this embedding and another."""
        if self.embedding is None:
            return 0.0
        
        other_embedding = np.array(other_embedding)
        
        # Calculate cosine similarity
        dot_product = np.dot(self.embedding, other_embedding)
        norm_a = np.linalg.norm(self.embedding)
        norm_b = np.linalg.norm(other_embedding)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def euclidean_distance(self, other_embedding: Union[List[float], np.ndarray]) -> float:
        """Calculate Euclidean distance between this embedding and another."""
        if self.embedding is None:
            return float('inf')
        
        other_embedding = np.array(other_embedding)
        return np.linalg.norm(self.embedding - other_embedding)
    
    def dot_product_similarity(self, other_embedding: Union[List[float], np.ndarray]) -> float:
        """Calculate dot product similarity between this embedding and another."""
        if self.embedding is None:
            return 0.0
        
        other_embedding = np.array(other_embedding)
        return np.dot(self.embedding, other_embedding)
    
    def normalize_embedding(self) -> np.ndarray:
        """Normalize the embedding to unit length."""
        if self.embedding is None:
            return None
        
        norm = np.linalg.norm(self.embedding)
        if norm == 0:
            return self.embedding
        
        return self.embedding / norm
    
    def update_metadata(self, new_metadata: Dict[str, Any]) -> None:
        """Update metadata fields."""
        self.metadata.update(new_metadata)
        
        # Update common fields
        self.source = self.metadata.get('source', self.source)
        self.source_id = self.metadata.get('source_id', self.source_id)
        self.timestamp = self.metadata.get('timestamp', self.timestamp)
        self.created_at = self.metadata.get('created_at', self.created_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vector object to dictionary."""
        return {
            "id": self.id,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "dimension": self.dimension,
            "metadata": self.metadata,
            "content": self.content,
            "source": self.source,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}', dimension={self.dimension}, source='{self.source}')"


class ElasticsearchVectorBase(VectorBase):
    """Vector base class using Elasticsearch as the vector database."""
    
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get Elasticsearch client for vector operations."""
        if cls._client is None:
            from elasticsearch import Elasticsearch
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
    
    def save(self, index: str = "vectors") -> bool:
        """Save vector to Elasticsearch."""
        try:
            doc = {
                "embedding": self.embedding.tolist() if self.embedding is not None else None,
                "content": self.content,
                "metadata": self.metadata,
                "created_at": self.created_at,
                "timestamp": self.timestamp
            }
            
            result = self.get_client().index(
                index=index,
                id=self.id,
                document=doc
            )
            
            logger.info(f"Saved vector {self.id} to Elasticsearch index {index}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector to Elasticsearch: {e}")
            return False
    
    def delete(self, index: str = "vectors") -> bool:
        """Delete vector from Elasticsearch."""
        try:
            self.get_client().delete(
                index=index,
                id=self.id
            )
            logger.info(f"Deleted vector {self.id} from Elasticsearch index {index}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vector from Elasticsearch: {e}")
            return False
    
    def find_similar(self, 
                    top_k: int = 10, 
                    threshold: float = 0.7,
                    filters: Dict[str, Any] = None,
                    index: str = "vectors") -> List[Tuple['VectorBase', float]]:
        """Find similar vectors using Elasticsearch vector search."""
        if self.embedding is None:
            return []
        
        try:
            # Build the query
            query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": self.embedding.tolist(),
                    "k": top_k,
                    "num_candidates": top_k * 2
                },
                "_source": ["content", "metadata", "created_at", "timestamp"]
            }
            
            # Add filters if provided
            if filters:
                query["knn"]["filter"] = {
                    "bool": {
                        "must": [{"term": {k: v}} for k, v in filters.items()]
                    }
                }
            
            result = self.get_client().search(
                index=index,
                body=query
            )
            
            similar_vectors = []
            for hit in result['hits']['hits']:
                if hit['_score'] >= threshold:
                    # Create vector object from hit
                    vector_obj = self.__class__(
                        vector_id=hit['_id'],
                        embedding=None,  # Don't load embedding for results
                        metadata=hit['_source'].get('metadata', {}),
                        content=hit['_source'].get('content')
                    )
                    similar_vectors.append((vector_obj, hit['_score']))
            
            return similar_vectors
        except Exception as e:
            logger.error(f"Error finding similar vectors: {e}")
            return []


class PineconeVectorBase(VectorBase):
    """Vector base class using Pinecone as the vector database."""
    
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get Pinecone client for vector operations."""
        if cls._client is None:
            try:
                import pinecone
                pinecone.init(
                    api_key=os.getenv("PINECONE_API_KEY"),
                    environment=os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
                )
                cls._client = pinecone
            except ImportError:
                logger.warning("Pinecone not installed. Install with: pip install pinecone-client")
                cls._client = None
        return cls._client
    
    def save(self, index_name: str = "default") -> bool:
        """Save vector to Pinecone."""
        try:
            client = self.get_client()
            if not client:
                return False
            
            index = client.Index(index_name)
            
            # Prepare vector data
            vector_data = (
                self.id,
                self.embedding.tolist() if self.embedding is not None else [],
                self.metadata
            )
            
            index.upsert([vector_data])
            logger.info(f"Saved vector {self.id} to Pinecone index {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector to Pinecone: {e}")
            return False
    
    def delete(self, index_name: str = "default") -> bool:
        """Delete vector from Pinecone."""
        try:
            client = self.get_client()
            if not client:
                return False
            
            index = client.Index(index_name)
            index.delete(ids=[self.id])
            logger.info(f"Deleted vector {self.id} from Pinecone index {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vector from Pinecone: {e}")
            return False
    
    def find_similar(self, 
                    top_k: int = 10, 
                    threshold: float = 0.7,
                    filters: Dict[str, Any] = None,
                    index_name: str = "default") -> List[Tuple['VectorBase', float]]:
        """Find similar vectors using Pinecone."""
        if self.embedding is None:
            return []
        
        try:
            client = self.get_client()
            if not client:
                return []
            
            index = client.Index(index_name)
            
            # Query similar vectors
            query_result = index.query(
                vector=self.embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                filter=filters
            )
            
            similar_vectors = []
            for match in query_result['matches']:
                if match['score'] >= threshold:
                    # Create vector object from match
                    vector_obj = self.__class__(
                        vector_id=match['id'],
                        embedding=None,  # Don't load embedding for results
                        metadata=match.get('metadata', {}),
                        content=match.get('metadata', {}).get('content')
                    )
                    similar_vectors.append((vector_obj, match['score']))
            
            return similar_vectors
        except Exception as e:
            logger.error(f"Error finding similar vectors in Pinecone: {e}")
            return [] 