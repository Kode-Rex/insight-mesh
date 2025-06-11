"""
Domain definitions using Python decorators and classes.
Replaces YAML-based domain configuration with code.
"""

from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

# Type models for better structure
class RelationshipType(Enum):
    HAS_MANY = "has_many"
    BELONGS_TO = "belongs_to"
    BELONGS_TO_MANY = "belongs_to_many"
    HAS_ONE = "has_one"

class AccessScope(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

@dataclass
class Relationship:
    domain: str
    type: RelationshipType
    foreign_key: Optional[str] = None
    through: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"domain": self.domain, "type": self.type.value}
        if self.foreign_key:
            result["foreign_key"] = self.foreign_key
        if self.through:
            result["through"] = self.through
        return result

@dataclass
class Permission:
    default: str = "read"
    roles: List[str] = field(default_factory=list)
    scopes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "default": self.default,
            "roles": self.roles,
            "scopes": self.scopes
        }

@dataclass
class DatabaseSource:
    database: str
    table: str
    filters: Dict[str, Any] = field(default_factory=dict)
    joins: List[Dict[str, str]] = field(default_factory=list)
    group_by: Optional[str] = None

@dataclass
class ElasticSource:
    elastic: str
    query_fields: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolContext:
    name: str
    access: Dict[str, List[str]]  # roles and scopes
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    use_cases: List[str] = field(default_factory=list)

@dataclass
class ToolConfig:
    base_url: Optional[str] = None
    rate_limit: Optional[int] = None
    timeout: Optional[int] = None
    max_results: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class AgentExecution:
    timeout: int = 300
    retry: int = 3
    cache: bool = True
    memory_limit: str = "512Mi"
    
    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

@dataclass
class AgentObservability:
    trace: bool = True
    metrics: bool = True
    logs: str = "info"
    
    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

@dataclass
class AgentTrigger:
    type: str
    pattern: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.pattern:
            result["pattern"] = self.pattern
        if self.path:
            result["path"] = self.path
        return result

# Domain, context, tool, and agent registries
_domains = {}
_contexts = {}
_tools = {}

def domain(name: str, description: str = ""):
    """Decorator to register a domain class"""
    def decorator(cls):
        cls._domain_name = name
        cls._description = description
        _domains[name] = cls
        return cls
    return decorator

def context(name: str, description: str = "", domains: List[str] = None):
    """Decorator to register a context class"""
    def decorator(cls):
        cls._context_name = name
        cls._description = description
        cls._domains = domains or []
        _contexts[name] = cls
        return cls
    return decorator

def tool(name: str, description: str = "", tool_type: str = "mcp"):
    """Decorator to register a tool class"""
    def decorator(cls):
        cls._tool_name = name
        cls._description = description
        cls._tool_type = tool_type
        _tools[name] = cls
        return cls
    return decorator

class BaseDomain(ABC):
    """Base class for all domains"""
    
    @property
    def description(self) -> str:
        """Domain description"""
        return getattr(self, '_description', '')
    
    @property
    @abstractmethod
    def schemas(self) -> Dict[str, Any]:
        """Database schemas for this domain"""
        pass
    
    @property
    @abstractmethod
    def contexts(self) -> List[str]:
        """Available contexts for this domain"""
        pass
    
    @property
    def permissions(self) -> Permission:
        """Permissions for this domain"""
        return Permission()
    
    @property
    def relationships(self) -> List[Relationship]:
        """Relationships to other domains"""
        return []

class BaseContext(ABC):
    """Base class for all contexts"""
    
    @property
    def description(self) -> str:
        """Context description"""
        return getattr(self, '_description', '')
    
    @property
    @abstractmethod
    def sources(self) -> List[Union[DatabaseSource, ElasticSource]]:
        """Data sources for this context"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> List[str]:
        """Available tools for this context"""
        pass
    
    @property
    def permissions(self) -> Permission:
        """Permissions for this context"""
        return Permission()
    
    @property
    def filters(self) -> Optional[Dict[str, Any]]:
        """Filters for this context"""
        return None
    
    @property
    def aggregations(self) -> Optional[Dict[str, Any]]:
        """Aggregations for this context"""
        return None

class BaseTool(ABC):
    """Base class for all tools"""
    
    @property
    def description(self) -> str:
        """Tool description"""
        return getattr(self, '_description', '')
    
    @property
    @abstractmethod
    def auth(self) -> str:
        """Authentication method"""
        pass
    
    @property
    @abstractmethod
    def contexts(self) -> List[ToolContext]:
        """Contexts this tool can be used in"""
        pass
    
    @property
    @abstractmethod
    def domains(self) -> List[str]:
        """Domains this tool applies to"""
        pass
    
    @property
    def config(self) -> ToolConfig:
        """Tool configuration"""
        return ToolConfig()
    
    @property
    def permissions(self) -> Permission:
        """Tool permissions"""
        return Permission()

# Domain definitions
@domain("person", "Represents people in the system, with relationships to messages, tasks, and tools")
class PersonDomain(BaseDomain):
    @property
    def schemas(self) -> Dict[str, Any]:
        return {
            "sql": {
                "insightmesh": "insightmesh_users",
                "slack": "slack_users"
            },
            "neo4j": "(:Person)",
            "elastic": "person_index"
        }
    
    @property
    def contexts(self) -> List[str]:
        return ["messages", "tasks", "channels"]
    
    @property
    def permissions(self) -> Permission:
        return Permission(
            default="read",
            roles=["analyst", "support", "admin"]
        )
    
    @property
    def relationships(self) -> List[Relationship]:
        return [
            Relationship("messages", RelationshipType.HAS_MANY, foreign_key="user_id"),
            Relationship("channels", RelationshipType.BELONGS_TO_MANY, through="channel_members")
        ]

@domain("messages", "Messages sent or received by people across different platforms")
class MessagesDomain(BaseDomain):
    @property
    def schemas(self) -> Dict[str, Any]:
        return {
            "sql": {
                "insightmesh": "messages",
                "slack": "slack_messages"
            },
            "neo4j": "(:Message)",
            "elastic": "message_index"
        }
    
    @property
    def contexts(self) -> List[str]:
        return ["conversations", "channels", "threads"]
    
    @property
    def relationships(self) -> List[Relationship]:
        return [
            Relationship("person", RelationshipType.BELONGS_TO, foreign_key="user_id"),
            Relationship("channels", RelationshipType.BELONGS_TO, foreign_key="channel_id")
        ]

@domain("channels", "Communication channels across different platforms (Slack, Teams, etc.)")
class ChannelsDomain(BaseDomain):
    @property
    def schemas(self) -> Dict[str, Any]:
        return {
            "sql": {"slack": "slack_channels"},
            "neo4j": "(:Channel)",
            "elastic": "channel_index"
        }
    
    @property
    def contexts(self) -> List[str]:
        return ["messages", "members", "activity"]

# Context definitions
@context("conversations", "Threaded conversations across platforms with full message history", 
         domains=["messages", "person", "channels"])
class ConversationsContext(BaseContext):
    @property
    def sources(self) -> List[Union[DatabaseSource, ElasticSource]]:
        return [
            DatabaseSource(
                database="insightmesh",
                table="conversations",
                joins=[
                    {"table": "messages", "on": "conversations.id = messages.conversation_id"},
                    {"table": "insightmesh_users", "on": "conversations.user_id = insightmesh_users.id"}
                ]
            ),
            DatabaseSource(
                database="slack",
                table="slack_messages",
                filters={"thread_ts": "NOT NULL"},
                group_by="thread_ts"
            ),
            ElasticSource(
                elastic="conversation_index",
                query_fields=["title", "summary", "tags"]
            )
        ]
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "notion", "webcat"]
    
    @property
    def aggregations(self) -> Dict[str, str]:
        return {
            "message_count": "COUNT(messages.id)",
            "last_activity": "MAX(messages.created_at)",
            "participants": "ARRAY_AGG(DISTINCT users.name)"
        }

# Tool definitions
@tool("slack", "Slack integration for messages, channels, and user management", "mcp")
class SlackTool(BaseTool):
    @property
    def auth(self) -> str:
        return "oauth2"
    
    @property
    def contexts(self) -> List[ToolContext]:
        return [
            ToolContext(
                name="messages",
                access={"roles": ["analyst", "support", "admin"], "scopes": ["read", "write"]},
                permissions={
                    "read": ["channel:history", "im:history", "mpim:history"],
                    "write": ["chat:write", "chat:write.public"]
                }
            ),
            ToolContext(
                name="channels",
                access={"roles": ["member", "admin"], "scopes": ["read", "write"]},
                permissions={
                    "read": ["channels:read", "groups:read"],
                    "write": ["channels:manage", "groups:write"]
                }
            ),
            ToolContext(
                name="person",
                access={"roles": ["admin"], "scopes": ["read"]},
                permissions={
                    "read": ["users:read", "users:read.email"]
                }
            )
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages", "channels"]
    
    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            base_url="https://slack.com/api",
            rate_limit=50,
            timeout=30
        )
    
    @property
    def filters(self) -> Dict[str, str]:
        return {
            "user_scope": "$user.slack_id",
            "team_scope": "$team.id"
        }

@tool("webcat", "Web search service for research and information gathering", "mcp")
class WebcatTool(BaseTool):
    @property
    def auth(self) -> str:
        return "none"
    
    @property
    def contexts(self) -> List[ToolContext]:
        return [
            ToolContext(
                name="messages",
                access={"roles": ["analyst", "researcher", "admin"], "scopes": ["read"]},
                use_cases=["fact_checking", "context_enrichment"]
            )
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages", "research"]
    
    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            rate_limit=100,
            timeout=15,
            max_results=10
        )

@tool("gmail", "Gmail integration for email management", "mcp")
class GmailTool(BaseTool):
    @property
    def auth(self) -> str:
        return "oauth2"
    
    @property
    def contexts(self) -> List[ToolContext]:
        return [
            ToolContext(
                name="messages",
                access={"roles": ["analyst", "support", "admin"], "scopes": ["read", "write"]},
                permissions={
                    "read": ["gmail.readonly", "gmail.metadata"],
                    "write": ["gmail.send", "gmail.compose"]
                }
            )
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages"]
    
    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            base_url="https://gmail.googleapis.com",
            rate_limit=250,
            timeout=30
        )

# Registry access functions
def get_domain(name: str) -> Optional[BaseDomain]:
    """Get domain instance by name"""
    domain_cls = _domains.get(name)
    return domain_cls() if domain_cls else None

def get_context(name: str) -> Optional[BaseContext]:
    """Get context instance by name"""
    context_cls = _contexts.get(name)
    return context_cls() if context_cls else None

def get_tool(name: str) -> Optional[BaseTool]:
    """Get tool instance by name"""
    tool_cls = _tools.get(name)
    return tool_cls() if tool_cls else None

def list_domains() -> List[str]:
    """List all registered domains"""
    return list(_domains.keys())

def list_contexts() -> List[str]:
    """List all registered contexts"""
    return list(_contexts.keys())

def list_tools() -> List[str]:
    """List all registered tools"""
    return list(_tools.keys())

def get_all_domains() -> Dict[str, BaseDomain]:
    """Get all registered domains"""
    return {name: cls() for name, cls in _domains.items()}

def get_all_contexts() -> Dict[str, BaseContext]:
    """Get all registered contexts"""
    return {name: cls() for name, cls in _contexts.items()}

def get_all_tools() -> Dict[str, BaseTool]:
    """Get all registered tools"""
    return {name: cls() for name, cls in _tools.items()} 