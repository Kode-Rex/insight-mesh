"""
Document domain model - composes document data from multiple sources.

This domain object aggregates documents from Slack files, email attachments,
uploaded documents, and other sources to provide unified document management
with business-relevant operations like content analysis and relationship tracking.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib

# Import the data layer models (when they exist)
# from data.slack import SlackFile
# from data.insightmesh import Document as InsightMeshDocument
# from data.email import EmailAttachment


class DocumentType(Enum):
    """Types of documents in the system"""
    SLACK_FILE = "slack_file"           # Slack uploaded file
    EMAIL_ATTACHMENT = "email_attachment"  # Email attachment
    UPLOADED_DOC = "uploaded_doc"       # Direct upload to InsightMesh
    GENERATED_DOC = "generated_doc"     # AI-generated document
    SHARED_LINK = "shared_link"         # Shared external document
    CODE_FILE = "code_file"             # Code repository file


class DocumentFormat(Enum):
    """Document formats"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class DocumentIdentity:
    """Represents a document's identity across different systems"""
    primary_id: str
    title: str
    document_type: DocumentType
    format: DocumentFormat
    source_id: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None


class Document:
    """
    Domain Document - composes document data from multiple sources.
    
    This class provides business-focused document management, aggregating
    documents from different platforms with content analysis, relationship
    tracking, and unified search capabilities.
    """
    
    def __init__(self, identity: DocumentIdentity):
        self.identity = identity
        self._slack_file: Optional[Any] = None  # Would be SlackFile when available
        self._insightmesh_document: Optional[Any] = None  # Would be InsightMeshDocument
        self._email_attachment: Optional[Dict[str, Any]] = None
        self._content: Optional[str] = None  # Extracted text content
        self._metadata: Dict[str, Any] = {}
        self._loaded_source: Optional[str] = None
        self._related_conversations: List[str] = []  # Conversation IDs
        self._related_users: List[str] = []  # User IDs who interacted with doc
    
    @classmethod
    async def from_slack_file(cls, slack_file: Any, session_factories: Dict[str, Any] = None) -> 'Document':
        """Create Document domain object from Slack file."""
        # Determine format from file extension or mime type
        file_format = cls._determine_format(
            getattr(slack_file, 'name', ''),
            getattr(slack_file, 'mimetype', '')
        )
        
        identity = DocumentIdentity(
            primary_id=f"slack_file_{getattr(slack_file, 'id', '')}",
            title=getattr(slack_file, 'name', 'Untitled'),
            document_type=DocumentType.SLACK_FILE,
            format=file_format,
            source_id=getattr(slack_file, 'id', ''),
            url=getattr(slack_file, 'url_private', None),
            size_bytes=getattr(slack_file, 'size', None),
            created_date=getattr(slack_file, 'created', None)
        )
        
        document = cls(identity)
        document._slack_file = slack_file
        document._loaded_source = 'slack'
        
        # Extract metadata
        document._metadata = {
            'channel_id': getattr(slack_file, 'channels', [None])[0] if getattr(slack_file, 'channels', []) else None,
            'user_id': getattr(slack_file, 'user', None),
            'is_public': getattr(slack_file, 'is_public', False),
            'comments_count': getattr(slack_file, 'comments_count', 0)
        }
        
        # Track related users
        if document._metadata.get('user_id'):
            document._related_users.append(document._metadata['user_id'])
        
        return document
    
    @classmethod
    async def from_email_attachment(cls, email_data: Dict[str, Any], attachment_data: Dict[str, Any]) -> 'Document':
        """Create Document domain object from email attachment."""
        file_format = cls._determine_format(
            attachment_data.get('filename', ''),
            attachment_data.get('content_type', '')
        )
        
        identity = DocumentIdentity(
            primary_id=f"email_attachment_{attachment_data.get('id', '')}",
            title=attachment_data.get('filename', 'Untitled'),
            document_type=DocumentType.EMAIL_ATTACHMENT,
            format=file_format,
            source_id=attachment_data.get('id', ''),
            size_bytes=attachment_data.get('size', None),
            created_date=email_data.get('date', None)
        )
        
        document = cls(identity)
        document._email_attachment = {**email_data, 'attachment': attachment_data}
        document._loaded_source = 'email'
        
        # Extract metadata
        document._metadata = {
            'email_subject': email_data.get('subject'),
            'sender': email_data.get('from_email'),
            'recipients': email_data.get('to', []),
            'message_id': email_data.get('message_id')
        }
        
        # Track related users
        if document._metadata.get('sender'):
            document._related_users.append(document._metadata['sender'])
        
        return document
    
    @classmethod
    async def from_uploaded_document(cls, doc_data: Dict[str, Any]) -> 'Document':
        """Create Document domain object from directly uploaded document."""
        file_format = cls._determine_format(
            doc_data.get('filename', ''),
            doc_data.get('content_type', '')
        )
        
        identity = DocumentIdentity(
            primary_id=f"uploaded_doc_{doc_data.get('id', '')}",
            title=doc_data.get('title', doc_data.get('filename', 'Untitled')),
            document_type=DocumentType.UPLOADED_DOC,
            format=file_format,
            source_id=doc_data.get('id', ''),
            file_path=doc_data.get('file_path'),
            size_bytes=doc_data.get('size', None),
            content_hash=doc_data.get('content_hash'),
            created_date=doc_data.get('created_at'),
            modified_date=doc_data.get('updated_at')
        )
        
        document = cls(identity)
        document._insightmesh_document = doc_data
        document._loaded_source = 'insightmesh'
        
        # Extract metadata
        document._metadata = {
            'uploader_id': doc_data.get('user_id'),
            'tags': doc_data.get('tags', []),
            'description': doc_data.get('description'),
            'is_public': doc_data.get('is_public', False)
        }
        
        # Track related users
        if document._metadata.get('uploader_id'):
            document._related_users.append(document._metadata['uploader_id'])
        
        return document
    
    @classmethod
    async def find_documents_by_content(cls, search_query: str, 
                                      document_types: List[DocumentType] = None,
                                      date_range: tuple = None,
                                      session_factories: Dict[str, Any] = None) -> List['Document']:
        """Find documents across all sources by content search."""
        documents = []
        document_types = document_types or list(DocumentType)
        start_date, end_date = date_range or (None, None)
        
        # Search Slack files (when implemented)
        if DocumentType.SLACK_FILE in document_types:
            slack_docs = await cls._search_slack_files(search_query, date_range, session_factories)
            documents.extend(slack_docs)
        
        # Search uploaded documents (when implemented)
        if DocumentType.UPLOADED_DOC in document_types:
            uploaded_docs = await cls._search_uploaded_documents(search_query, date_range, session_factories)
            documents.extend(uploaded_docs)
        
        # Search email attachments (when implemented)
        if DocumentType.EMAIL_ATTACHMENT in document_types:
            email_docs = await cls._search_email_attachments(search_query, date_range, session_factories)
            documents.extend(email_docs)
        
        return documents
    
    @classmethod
    async def find_documents_by_user(cls, user_id: str,
                                   document_types: List[DocumentType] = None,
                                   date_range: tuple = None,
                                   session_factories: Dict[str, Any] = None) -> List['Document']:
        """Find all documents associated with a user across all sources."""
        documents = []
        document_types = document_types or list(DocumentType)
        
        # This would search across all sources for documents uploaded, shared, or commented on by the user
        # Implementation would depend on available data models
        
        return documents
    
    @classmethod
    async def find_documents_in_conversation(cls, conversation_id: str,
                                           session_factories: Dict[str, Any] = None) -> List['Document']:
        """Find all documents shared or referenced in a conversation."""
        documents = []
        
        # This would find documents shared in Slack channels, attached to emails in threads, etc.
        # Implementation would depend on conversation context and available data
        
        return documents
    
    @classmethod
    def _determine_format(cls, filename: str, content_type: str = '') -> DocumentFormat:
        """Determine document format from filename and content type."""
        filename_lower = filename.lower()
        
        # Check by file extension
        if filename_lower.endswith(('.pdf',)):
            return DocumentFormat.PDF
        elif filename_lower.endswith(('.docx', '.doc')):
            return DocumentFormat.DOCX
        elif filename_lower.endswith(('.txt',)):
            return DocumentFormat.TXT
        elif filename_lower.endswith(('.md', '.markdown')):
            return DocumentFormat.MD
        elif filename_lower.endswith(('.html', '.htm')):
            return DocumentFormat.HTML
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg')):
            return DocumentFormat.IMAGE
        elif filename_lower.endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
            return DocumentFormat.VIDEO
        elif filename_lower.endswith(('.mp3', '.wav', '.flac', '.aac')):
            return DocumentFormat.AUDIO
        elif filename_lower.endswith(('.xlsx', '.xls', '.csv')):
            return DocumentFormat.SPREADSHEET
        elif filename_lower.endswith(('.pptx', '.ppt')):
            return DocumentFormat.PRESENTATION
        elif filename_lower.endswith(('.py', '.js', '.java', '.cpp', '.c', '.go', '.rs', '.rb')):
            return DocumentFormat.CODE
        
        # Check by content type
        if 'pdf' in content_type:
            return DocumentFormat.PDF
        elif 'word' in content_type or 'document' in content_type:
            return DocumentFormat.DOCX
        elif 'text' in content_type:
            return DocumentFormat.TXT
        elif 'image' in content_type:
            return DocumentFormat.IMAGE
        elif 'video' in content_type:
            return DocumentFormat.VIDEO
        elif 'audio' in content_type:
            return DocumentFormat.AUDIO
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return DocumentFormat.SPREADSHEET
        elif 'presentation' in content_type or 'powerpoint' in content_type:
            return DocumentFormat.PRESENTATION
        
        return DocumentFormat.UNKNOWN
    
    @classmethod
    async def _search_slack_files(cls, query: str, date_range: tuple, session_factories: Dict[str, Any]) -> List['Document']:
        """Search Slack files (implementation depends on SlackFile model)."""
        return []
    
    @classmethod
    async def _search_uploaded_documents(cls, query: str, date_range: tuple, session_factories: Dict[str, Any]) -> List['Document']:
        """Search uploaded documents (implementation depends on Document model)."""
        return []
    
    @classmethod
    async def _search_email_attachments(cls, query: str, date_range: tuple, session_factories: Dict[str, Any]) -> List['Document']:
        """Search email attachments (implementation depends on email data)."""
        return []
    
    # Business Logic Properties
    @property
    def title(self) -> str:
        """Get document title."""
        return self.identity.title
    
    @property
    def size_mb(self) -> Optional[float]:
        """Get document size in MB."""
        if self.identity.size_bytes:
            return round(self.identity.size_bytes / (1024 * 1024), 2)
        return None
    
    @property
    def age_days(self) -> Optional[int]:
        """Get document age in days."""
        if self.identity.created_date:
            return (datetime.utcnow() - self.identity.created_date).days
        return None
    
    @property
    def is_recent(self) -> bool:
        """Check if document was created recently (within 7 days)."""
        return self.age_days is not None and self.age_days <= 7
    
    @property
    def is_large(self) -> bool:
        """Check if document is large (>10MB)."""
        return self.size_mb is not None and self.size_mb > 10
    
    @property
    def is_text_based(self) -> bool:
        """Check if document contains extractable text."""
        return self.identity.format in [
            DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.TXT,
            DocumentFormat.MD, DocumentFormat.HTML, DocumentFormat.CODE
        ]
    
    # Business Logic Methods
    async def extract_content(self) -> Optional[str]:
        """Extract text content from the document."""
        if self._content:
            return self._content
        
        if not self.is_text_based:
            return None
        
        # This would implement content extraction based on document type
        # For now, return placeholder
        if self.identity.format == DocumentFormat.TXT:
            # Would read text file content
            pass
        elif self.identity.format == DocumentFormat.PDF:
            # Would use PDF extraction library
            pass
        elif self.identity.format == DocumentFormat.DOCX:
            # Would use DOCX extraction library
            pass
        
        return None
    
    def calculate_content_hash(self, content: str = None) -> str:
        """Calculate hash of document content for deduplication."""
        if content is None:
            content = self._content or ""
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    def add_related_conversation(self, conversation_id: str):
        """Add a conversation that references this document."""
        if conversation_id not in self._related_conversations:
            self._related_conversations.append(conversation_id)
    
    def add_related_user(self, user_id: str):
        """Add a user who interacted with this document."""
        if user_id not in self._related_users:
            self._related_users.append(user_id)
    
    def is_related_to_conversation(self, conversation_id: str) -> bool:
        """Check if document is related to a specific conversation."""
        return conversation_id in self._related_conversations
    
    def is_related_to_user(self, user_id: str) -> bool:
        """Check if document is related to a specific user."""
        return user_id in self._related_users
    
    def get_sharing_context(self) -> Dict[str, Any]:
        """Get context about how/where this document was shared."""
        context = {
            'source': self.identity.document_type.value,
            'related_conversations': len(self._related_conversations),
            'related_users': len(self._related_users),
            'is_public': self._metadata.get('is_public', False)
        }
        
        if self._loaded_source == 'slack':
            context['slack'] = {
                'channel_id': self._metadata.get('channel_id'),
                'comments_count': self._metadata.get('comments_count', 0)
            }
        elif self._loaded_source == 'email':
            context['email'] = {
                'subject': self._metadata.get('email_subject'),
                'recipients_count': len(self._metadata.get('recipients', []))
            }
        
        return context
    
    # Data Access
    def get_slack_file(self) -> Optional[Any]:
        """Get the underlying Slack file data object."""
        return self._slack_file
    
    def get_insightmesh_document(self) -> Optional[Any]:
        """Get the underlying InsightMesh document data object."""
        return self._insightmesh_document
    
    def get_email_attachment(self) -> Optional[Dict[str, Any]]:
        """Get the underlying email attachment data."""
        return self._email_attachment
    
    def get_source_data(self) -> Optional[Any]:
        """Get the underlying source data object."""
        if self._loaded_source == 'slack':
            return self._slack_file
        elif self._loaded_source == 'insightmesh':
            return self._insightmesh_document
        elif self._loaded_source == 'email':
            return self._email_attachment
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get document metadata."""
        return self._metadata.copy()
    
    def get_related_conversations(self) -> List[str]:
        """Get list of related conversation IDs."""
        return self._related_conversations.copy()
    
    def get_related_users(self) -> List[str]:
        """Get list of related user IDs."""
        return self._related_users.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'identity': {
                'id': self.identity.primary_id,
                'title': self.identity.title,
                'type': self.identity.document_type.value,
                'format': self.identity.format.value,
                'source_id': self.identity.source_id,
                'url': self.identity.url,
                'file_path': self.identity.file_path
            },
            'properties': {
                'size_mb': self.size_mb,
                'age_days': self.age_days,
                'is_recent': self.is_recent,
                'is_large': self.is_large,
                'is_text_based': self.is_text_based,
                'content_hash': self.identity.content_hash
            },
            'relationships': {
                'related_conversations': len(self._related_conversations),
                'related_users': len(self._related_users)
            },
            'dates': {
                'created': self.identity.created_date.isoformat() if self.identity.created_date else None,
                'modified': self.identity.modified_date.isoformat() if self.identity.modified_date else None
            },
            'sharing_context': self.get_sharing_context(),
            'source': self._loaded_source
        }
    
    def __repr__(self) -> str:
        size_info = f", {self.size_mb}MB" if self.size_mb else ""
        return f"Document(id='{self.identity.primary_id}', title='{self.identity.title}', type='{self.identity.document_type.value}'{size_info})" 