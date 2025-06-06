from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Metadata for a document returned from Elasticsearch"""
    source: str = Field(default="unknown", description="Source of the document")
    file_name: Optional[str] = Field(default=None, description="File name if applicable")
    created_time: Optional[datetime] = Field(default=None, description="Creation time")
    modified_time: Optional[datetime] = Field(default=None, description="Last modified time")
    web_link: Optional[str] = Field(default=None, description="Web link to the document")
    permissions: List[Dict[str, Any]] = Field(default_factory=list, description="Access permissions")
    is_public: bool = Field(default=False, description="Whether the document is publicly accessible")
    
    def dict(self):
        return {
            "source": self.source,
            "file_name": self.file_name,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "web_link": self.web_link,
            "permissions": self.permissions,
            "is_public": self.is_public
        }

class Document(BaseModel):
    """Document model returned from Elasticsearch"""
    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    score: float = Field(..., description="Relevance score")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    
    def dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata.dict()
        }

class ContextRequest(BaseModel):
    """Request model for context retrieval"""
    auth_token: str = Field(..., description="JWT token for user authentication")
    token_type: str = Field(..., description="Type of JWT token (e.g., OpenWebUI)")
    prompt: str = Field(..., description="User's current prompt")
    history_summary: Optional[str] = Field(None, description="Summary of conversation history")
    
    def dict(self):
        return {
            "auth_token": self.auth_token,
            "token_type": self.token_type,
            "prompt": self.prompt,
            "history_summary": self.history_summary
        }

class ContextItem(BaseModel):
    """A single context item to be injected into the conversation"""
    content: str = Field(..., description="The content to be injected")
    role: str = Field("system", description="The role of the context (system, user, assistant)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about this context item")
    
    def dict(self):
        return {
            "content": self.content,
            "role": self.role,
            "metadata": self.metadata
        }

class UserInfo(BaseModel):
    """User information extracted from token"""
    id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User's email address")
    name: Optional[str] = Field(None, description="User's name")
    is_active: bool = Field(True, description="Whether the user is active")
    token_type: str = Field(..., description="Type of authentication token")
    
    def dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "token_type": self.token_type
        }

class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval process"""
    cache_hit: bool = Field(default=False, description="Whether the result was from cache")
    retrieval_time_ms: int = Field(..., description="Time taken for retrieval in milliseconds")
    
    def dict(self):
        return {
            "cache_hit": self.cache_hit,
            "retrieval_time_ms": self.retrieval_time_ms
        }

class ContextSource(BaseModel):
    """Source of context items"""
    type: str = Field(..., description="Type of context source")
    count: int = Field(..., description="Number of items from this source")
    
    def dict(self):
        return {
            "type": self.type,
            "count": self.count
        }

class ResponseMetadata(BaseModel):
    """Metadata for context response"""
    user: UserInfo = Field(..., description="User information")
    token_type: str = Field(..., description="Type of JWT token")
    timestamp: str = Field(..., description="ISO format timestamp")
    context_sources: List[ContextSource] = Field(..., description="Sources of context items")
    retrieval_metadata: RetrievalMetadata = Field(..., description="Retrieval performance metrics")
    
    def dict(self):
        return {
            "user": self.user.dict(),
            "token_type": self.token_type,
            "timestamp": self.timestamp,
            "context_sources": [source.dict() for source in self.context_sources],
            "retrieval_metadata": self.retrieval_metadata.dict()
        }

class ContextResponse(BaseModel):
    """Response following the MCP protocol"""
    context_items: List[ContextItem] = Field(..., description="List of context items to be injected into the conversation")
    metadata: ResponseMetadata = Field(..., description="Additional metadata about the context retrieval")
    
    def dict(self):
        return {
            "context_items": [item.dict() for item in self.context_items],
            "metadata": self.metadata.dict()
        }

class DocumentResult(BaseModel):
    """Simple document result model for internal use"""
    content: str = Field(..., description="Document content")
    source: str = Field(default="unknown", description="Source of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the document, including links")
    
    def dict(self):
        return {
            "content": self.content,
            "source": self.source,
            "metadata": self.metadata
        }

class ContextResult(BaseModel):
    """Internal context result model"""
    documents: List[DocumentResult] = Field(default_factory=list)
    retrieval_time_ms: int = Field(..., description="Time taken for retrieval in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether the result was from cache")
    
    def dict(self):
        return {
            "documents": [doc.dict() for doc in self.documents],
            "retrieval_time_ms": self.retrieval_time_ms,
            "cache_hit": self.cache_hit
        } 