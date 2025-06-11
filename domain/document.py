"""
Document domain model - focused on Google Drive and Slack document management.

This domain object provides a business interface for Google Drive documents
and Slack files that have been indexed by the Dagster pipeline into Elasticsearch and Neo4j.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Import Elasticsearch for document search
try:
    from elasticsearch import Elasticsearch
    import os
    
    # Initialize Elasticsearch connection
    es = Elasticsearch(
        hosts=[{
            "scheme": "http",
            "host": os.getenv("ELASTICSEARCH_HOST", "localhost"),
            "port": int(os.getenv("ELASTICSEARCH_PORT", "9200")),
        }]
    )
except ImportError:
    es = None


class DocumentSource(Enum):
    """Document sources"""
    GOOGLE_DRIVE = "google_drive"
    SLACK = "slack"


class DocumentFormat(Enum):
    """Document formats"""
    GOOGLE_DOC = "google_doc"           # Google Docs
    GOOGLE_SHEET = "google_sheet"       # Google Sheets  
    GOOGLE_SLIDE = "google_slide"       # Google Slides
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class DocumentIdentity:
    """Represents a document's identity across Google Drive and Slack"""
    file_id: str                        # Google Drive file ID or Slack file ID
    title: str
    source: DocumentSource
    format: DocumentFormat
    web_link: Optional[str] = None
    size_bytes: Optional[int] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    mime_type: Optional[str] = None
    # Slack specific fields
    channel_id: Optional[str] = None
    user_id: Optional[str] = None


class Document:
    """
    Domain Document - focused on Google Drive and Slack documents.
    
    This class provides business-focused document management for Google Drive
    files and Slack files that have been indexed by the Dagster pipeline.
    """
    
    def __init__(self, identity: DocumentIdentity):
        self.identity = identity
        self._content: Optional[str] = None
        self._permissions: List[Dict[str, Any]] = []
        self._is_public: bool = False
        self._related_conversations: List[str] = []  # Conversation IDs
        self._related_users: List[str] = []  # User IDs who interacted with doc
        # Slack specific metadata
        self._slack_metadata: Dict[str, Any] = {}
    
    @classmethod
    async def from_google_drive_data(cls, drive_data: Dict[str, Any]) -> 'Document':
        """Create Document from Google Drive indexed data."""
        # Determine format from MIME type
        file_format = cls._determine_format_from_mime(drive_data.get('mime_type', ''))
        
        identity = DocumentIdentity(
            file_id=drive_data.get('file_id', ''),
            title=drive_data.get('file_name', 'Untitled'),
            source=DocumentSource.GOOGLE_DRIVE,
            format=file_format,
            web_link=drive_data.get('web_link'),
            size_bytes=drive_data.get('size'),
            created_date=drive_data.get('created_time'),
            modified_date=drive_data.get('modified_time'),
            mime_type=drive_data.get('mime_type')
        )
        
        document = cls(identity)
        document._content = drive_data.get('content', '')
        document._permissions = drive_data.get('permissions', [])
        document._is_public = drive_data.get('is_public', False)
        
        return document
    
    @classmethod
    async def from_slack_data(cls, slack_data: Dict[str, Any]) -> 'Document':
        """Create Document from Slack file data."""
        # Determine format from MIME type or filename
        file_format = cls._determine_format_from_mime(slack_data.get('mimetype', ''))
        if file_format == DocumentFormat.UNKNOWN:
            file_format = cls._determine_format_from_filename(slack_data.get('name', ''))
        
        identity = DocumentIdentity(
            file_id=slack_data.get('id', ''),
            title=slack_data.get('name', 'Untitled'),
            source=DocumentSource.SLACK,
            format=file_format,
            web_link=slack_data.get('url_private') or slack_data.get('permalink'),
            size_bytes=slack_data.get('size'),
            created_date=slack_data.get('created'),
            mime_type=slack_data.get('mimetype'),
            channel_id=slack_data.get('channels', [None])[0] if slack_data.get('channels') else None,
            user_id=slack_data.get('user')
        )
        
        document = cls(identity)
        document._content = slack_data.get('content', '')
        document._is_public = slack_data.get('is_public', False)
        
        # Store Slack-specific metadata
        document._slack_metadata = {
            'channels': slack_data.get('channels', []),
            'comments_count': slack_data.get('comments_count', 0),
            'is_external': slack_data.get('is_external', False),
            'external_type': slack_data.get('external_type'),
            'pretty_type': slack_data.get('pretty_type'),
            'preview': slack_data.get('preview')
        }
        
        # Track related users
        if identity.user_id:
            document._related_users.append(identity.user_id)
        
        return document
    
    @classmethod
    async def search_by_content(cls, query: str, limit: int = 20, sources: List[DocumentSource] = None) -> List['Document']:
        """Search documents by content across Google Drive and/or Slack"""
        if not es:
            raise RuntimeError("Elasticsearch not available")
        
        # Default to searching both sources
        if sources is None:
            sources = [DocumentSource.GOOGLE_DRIVE, DocumentSource.SLACK]
        
        documents = []
        
        # Search Google Drive if requested
        if DocumentSource.GOOGLE_DRIVE in sources:
            try:
                response = es.search(
                    index="google_drive_files",
                    body={
                        "query": {
                            "multi_match": {
                                "query": query,
                                "fields": ["content", "meta.file_name^2"],
                                "type": "best_fields"
                            }
                        },
                        "size": limit,
                        "_source": ["content", "meta"]
                    }
                )
                
                for hit in response["hits"]["hits"]:
                    meta = hit["_source"]["meta"]
                    drive_data = {
                        'file_id': meta["file_id"],
                        'file_name': meta["file_name"],
                        'mime_type': meta["mime_type"],
                        'content': hit["_source"]["content"],
                        'web_link': meta.get("web_link"),
                        'created_time': meta.get("created_time"),
                        'modified_time': meta.get("modified_time"),
                        'is_public': meta.get("is_public", False),
                        'permissions': meta.get("permissions", [])
                    }
                    doc = await cls.from_google_drive_data(drive_data)
                    documents.append(doc)
            except Exception as e:
                print(f"Error searching Google Drive documents: {e}")
        
        # Search Slack if requested
        if DocumentSource.SLACK in sources:
            try:
                response = es.search(
                    index="slack_messages",  # Assuming Slack files are indexed here
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "multi_match": {
                                            "query": query,
                                            "fields": ["content", "files.name^2"],
                                            "type": "best_fields"
                                        }
                                    },
                                    {
                                        "exists": {
                                            "field": "files"
                                        }
                                    }
                                ]
                            }
                        },
                        "size": limit,
                        "_source": ["files", "channel", "user", "ts"]
                    }
                )
                
                for hit in response["hits"]["hits"]:
                    files = hit["_source"].get("files", [])
                    for file_data in files:
                        slack_data = {
                            **file_data,
                            'channels': [hit["_source"].get("channel")],
                            'user': hit["_source"].get("user"),
                            'created': hit["_source"].get("ts")
                        }
                        doc = await cls.from_slack_data(slack_data)
                        documents.append(doc)
            except Exception as e:
                print(f"Error searching Slack documents: {e}")
        
        return documents[:limit]  # Ensure we don't exceed the limit
    
    @classmethod
    async def get_by_file_id(cls, file_id: str, source: DocumentSource) -> Optional['Document']:
        """Get a specific document by its file ID and source"""
        if not es:
            raise RuntimeError("Elasticsearch not available")
        
        try:
            if source == DocumentSource.GOOGLE_DRIVE:
                response = es.get(
                    index="google_drive_files",
                    id=file_id,
                    _source=["content", "meta"]
                )
                
                meta = response["_source"]["meta"]
                drive_data = {
                    'file_id': meta["file_id"],
                    'file_name': meta["file_name"],
                    'mime_type': meta["mime_type"],
                    'content': response["_source"]["content"],
                    'web_link': meta.get("web_link"),
                    'created_time': meta.get("created_time"),
                    'modified_time': meta.get("modified_time"),
                    'is_public': meta.get("is_public", False),
                    'permissions': meta.get("permissions", [])
                }
                return await cls.from_google_drive_data(drive_data)
            
            elif source == DocumentSource.SLACK:
                # Search for Slack file by ID
                response = es.search(
                    index="slack_messages",
                    body={
                        "query": {
                            "nested": {
                                "path": "files",
                                "query": {
                                    "term": {
                                        "files.id": file_id
                                    }
                                }
                            }
                        },
                        "size": 1,
                        "_source": ["files", "channel", "user", "ts"]
                    }
                )
                
                if response["hits"]["hits"]:
                    hit = response["hits"]["hits"][0]
                    files = hit["_source"].get("files", [])
                    for file_data in files:
                        if file_data.get("id") == file_id:
                            slack_data = {
                                **file_data,
                                'channels': [hit["_source"].get("channel")],
                                'user': hit["_source"].get("user"),
                                'created': hit["_source"].get("ts")
                            }
                            return await cls.from_slack_data(slack_data)
                
        except Exception as e:
            print(f"Error getting document {file_id}: {e}")
        
        return None
    
    @classmethod
    async def list_recent_documents(cls, days: int = 7, limit: int = 20, sources: List[DocumentSource] = None) -> List['Document']:
        """List recently modified documents from Google Drive and/or Slack"""
        if not es:
            raise RuntimeError("Elasticsearch not available")
        
        if sources is None:
            sources = [DocumentSource.GOOGLE_DRIVE, DocumentSource.SLACK]
        
        documents = []
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get recent Google Drive documents
        if DocumentSource.GOOGLE_DRIVE in sources:
            try:
                response = es.search(
                    index="google_drive_files",
                    body={
                        "query": {
                            "range": {
                                "meta.modified_time": {
                                    "gte": threshold_date
                                }
                            }
                        },
                        "sort": [
                            {"meta.modified_time": {"order": "desc"}}
                        ],
                        "size": limit,
                        "_source": ["content", "meta"]
                    }
                )
                
                for hit in response["hits"]["hits"]:
                    meta = hit["_source"]["meta"]
                    drive_data = {
                        'file_id': meta["file_id"],
                        'file_name': meta["file_name"],
                        'mime_type': meta["mime_type"],
                        'content': hit["_source"]["content"],
                        'web_link': meta.get("web_link"),
                        'created_time': meta.get("created_time"),
                        'modified_time': meta.get("modified_time"),
                        'is_public': meta.get("is_public", False),
                        'permissions': meta.get("permissions", [])
                    }
                    doc = await cls.from_google_drive_data(drive_data)
                    documents.append(doc)
            except Exception as e:
                print(f"Error getting recent Google Drive documents: {e}")
        
        # Get recent Slack files
        if DocumentSource.SLACK in sources:
            try:
                response = es.search(
                    index="slack_messages",
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "range": {
                                            "ts": {
                                                "gte": threshold_date
                                            }
                                        }
                                    },
                                    {
                                        "exists": {
                                            "field": "files"
                                        }
                                    }
                                ]
                            }
                        },
                        "sort": [
                            {"ts": {"order": "desc"}}
                        ],
                        "size": limit,
                        "_source": ["files", "channel", "user", "ts"]
                    }
                )
                
                for hit in response["hits"]["hits"]:
                    files = hit["_source"].get("files", [])
                    for file_data in files:
                        slack_data = {
                            **file_data,
                            'channels': [hit["_source"].get("channel")],
                            'user': hit["_source"].get("user"),
                            'created': hit["_source"].get("ts")
                        }
                        doc = await cls.from_slack_data(slack_data)
                        documents.append(doc)
            except Exception as e:
                print(f"Error getting recent Slack documents: {e}")
        
        # Sort all documents by date and limit
        documents.sort(key=lambda d: d.identity.modified_date or d.identity.created_date or "", reverse=True)
        return documents[:limit]
    
    @classmethod
    def _determine_format_from_mime(cls, mime_type: str) -> DocumentFormat:
        """Determine document format from MIME type."""
        if mime_type == "application/vnd.google-apps.document":
            return DocumentFormat.GOOGLE_DOC
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            return DocumentFormat.GOOGLE_SHEET
        elif mime_type == "application/vnd.google-apps.presentation":
            return DocumentFormat.GOOGLE_SLIDE
        elif "pdf" in mime_type:
            return DocumentFormat.PDF
        elif "word" in mime_type or "document" in mime_type:
            return DocumentFormat.DOCX
        elif "text" in mime_type:
            return DocumentFormat.TXT
        elif "image" in mime_type:
            return DocumentFormat.IMAGE
        elif "video" in mime_type:
            return DocumentFormat.VIDEO
        elif "audio" in mime_type:
            return DocumentFormat.AUDIO
        
        return DocumentFormat.UNKNOWN
    
    @classmethod
    def _determine_format_from_filename(cls, filename: str) -> DocumentFormat:
        """Determine document format from filename."""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(('.pdf',)):
            return DocumentFormat.PDF
        elif filename_lower.endswith(('.docx', '.doc')):
            return DocumentFormat.DOCX
        elif filename_lower.endswith(('.txt',)):
            return DocumentFormat.TXT
        elif filename_lower.endswith(('.md', '.markdown')):
            return DocumentFormat.MD
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg')):
            return DocumentFormat.IMAGE
        elif filename_lower.endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
            return DocumentFormat.VIDEO
        elif filename_lower.endswith(('.mp3', '.wav', '.flac', '.aac')):
            return DocumentFormat.AUDIO
        elif filename_lower.endswith(('.py', '.js', '.java', '.cpp', '.c', '.go', '.rs', '.rb')):
            return DocumentFormat.CODE
        
        return DocumentFormat.UNKNOWN
    
    # Business Logic Properties
    @property
    def title(self) -> str:
        """Get document title."""
        return self.identity.title
    
    @property
    def file_id(self) -> str:
        """Get file ID."""
        return self.identity.file_id
    
    @property
    def source(self) -> DocumentSource:
        """Get document source."""
        return self.identity.source
    
    @property
    def size_mb(self) -> Optional[float]:
        """Get document size in MB."""
        if self.identity.size_bytes:
            return round(self.identity.size_bytes / (1024 * 1024), 2)
        return None
    
    @property
    def is_google_native(self) -> bool:
        """Check if this is a native Google document (Docs, Sheets, Slides)"""
        return self.identity.format in [
            DocumentFormat.GOOGLE_DOC, 
            DocumentFormat.GOOGLE_SHEET, 
            DocumentFormat.GOOGLE_SLIDE
        ]
    
    @property
    def is_slack_file(self) -> bool:
        """Check if this is a Slack file"""
        return self.identity.source == DocumentSource.SLACK
    
    @property
    def is_text_based(self) -> bool:
        """Check if document contains readable text."""
        return self.identity.format in [
            DocumentFormat.GOOGLE_DOC, DocumentFormat.GOOGLE_SHEET,
            DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.TXT, DocumentFormat.MD
        ]
    
    @property
    def content(self) -> str:
        """Get document content."""
        return self._content or ""
    
    @property
    def is_public(self) -> bool:
        """Check if document is publicly accessible."""
        return self._is_public
    
    @property
    def permissions(self) -> List[Dict[str, Any]]:
        """Get document permissions."""
        return self._permissions.copy()
    
    @property
    def slack_metadata(self) -> Dict[str, Any]:
        """Get Slack-specific metadata."""
        return self._slack_metadata.copy()
    
    # Business Logic Methods
    def add_related_conversation(self, conversation_id: str):
        """Add a conversation that references this document."""
        if conversation_id not in self._related_conversations:
            self._related_conversations.append(conversation_id)
    
    def add_related_user(self, user_id: str):
        """Add a user who interacted with this document."""
        if user_id not in self._related_users:
            self._related_users.append(user_id)
    
    def get_sharing_context(self) -> Dict[str, Any]:
        """Get context about document sharing and access."""
        context = {
            'source': self.identity.source.value,
            'is_public': self._is_public,
            'related_conversations': len(self._related_conversations),
            'related_users': len(self._related_users),
            'web_link': self.identity.web_link
        }
        
        if self.is_slack_file:
            context['slack'] = {
                'channel_id': self.identity.channel_id,
                'user_id': self.identity.user_id,
                'channels': self._slack_metadata.get('channels', []),
                'comments_count': self._slack_metadata.get('comments_count', 0),
                'is_external': self._slack_metadata.get('is_external', False)
            }
        else:
            context['google_drive'] = {
                'permissions_count': len(self._permissions),
                'mime_type': self.identity.mime_type
            }
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'file_id': self.identity.file_id,
            'title': self.identity.title,
            'source': self.identity.source.value,
            'format': self.identity.format.value,
            'mime_type': self.identity.mime_type,
            'web_link': self.identity.web_link,
            'size_mb': self.size_mb,
            'is_google_native': self.is_google_native,
            'is_slack_file': self.is_slack_file,
            'is_text_based': self.is_text_based,
            'is_public': self._is_public,
            'created_date': self.identity.created_date,
            'modified_date': self.identity.modified_date,
            'channel_id': self.identity.channel_id,
            'user_id': self.identity.user_id,
            'sharing_context': self.get_sharing_context()
        }
    
    def __repr__(self) -> str:
        size_info = f", {self.size_mb}MB" if self.size_mb else ""
        return f"Document(file_id='{self.identity.file_id}', title='{self.identity.title}', source='{self.identity.source.value}', format='{self.identity.format.value}'{size_info})"


# Convenience functions for common operations
async def search_google_docs(query: str, limit: int = 20) -> List[Document]:
    """Search for Google Docs specifically"""
    docs = await Document.search_by_content(query, limit, sources=[DocumentSource.GOOGLE_DRIVE])
    return [doc for doc in docs if doc.identity.format == DocumentFormat.GOOGLE_DOC]

async def search_slack_files(query: str, limit: int = 20) -> List[Document]:
    """Search for Slack files specifically"""
    return await Document.search_by_content(query, limit, sources=[DocumentSource.SLACK])

async def get_recent_google_drive_activity(days: int = 7) -> List[Document]:
    """Get recent Google Drive document activity"""
    return await Document.list_recent_documents(days, sources=[DocumentSource.GOOGLE_DRIVE])

async def get_recent_slack_files(days: int = 7) -> List[Document]:
    """Get recent Slack file activity"""
    return await Document.list_recent_documents(days, sources=[DocumentSource.SLACK])

async def get_recent_document_activity(days: int = 7) -> List[Document]:
    """Get recent document activity from both sources"""
    return await Document.list_recent_documents(days) 