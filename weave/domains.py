"""
Domain definitions using Python decorators and classes.
Replaces YAML-based domain configuration with code.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Domain registry
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
        """Schema mappings across databases"""
        pass
    
    @property
    @abstractmethod
    def contexts(self) -> List[str]:
        """Available contexts for this domain"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> List[str]:
        """Available tools for this domain"""
        pass
    
    @property
    def permissions(self) -> Dict[str, Any]:
        """Default permissions for this domain"""
        return {"default": "read", "roles": ["user"]}
    
    @property
    def relationships(self) -> List[Dict[str, Any]]:
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
    def sources(self) -> List[Dict[str, Any]]:
        """Data sources for this context"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> List[str]:
        """Available tools for this context"""
        pass
    
    @property
    def permissions(self) -> Dict[str, Any]:
        """Permissions for this context"""
        return {"default": "read"}
    
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
    def contexts(self) -> List[Dict[str, Any]]:
        """Context-specific configurations"""
        pass
    
    @property
    @abstractmethod
    def domains(self) -> List[str]:
        """Domains this tool can work with"""
        pass
    
    @property
    def config(self) -> Dict[str, Any]:
        """Tool configuration"""
        return {}
    
    @property
    def permissions(self) -> Dict[str, Any]:
        """Default permissions"""
        return {"default": "read"}

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
    def tools(self) -> List[str]:
        return ["slack", "webcat", "gmail"]
    
    @property
    def permissions(self) -> Dict[str, Any]:
        return {
            "default": "read",
            "roles": ["analyst", "support", "admin"]
        }
    
    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return [
            {"domain": "messages", "type": "has_many", "foreign_key": "user_id"},
            {"domain": "channels", "type": "belongs_to_many", "through": "channel_members"}
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
    def tools(self) -> List[str]:
        return ["slack", "gmail", "notion"]
    
    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return [
            {"domain": "person", "type": "belongs_to", "foreign_key": "user_id"},
            {"domain": "channels", "type": "belongs_to", "foreign_key": "channel_id"}
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
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "teams"]

# Context definitions
@context("conversations", "Threaded conversations across platforms with full message history", 
         domains=["messages", "person", "channels"])
class ConversationsContext(BaseContext):
    @property
    def sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "database": "insightmesh",
                "table": "conversations",
                "joins": [
                    {"table": "messages", "on": "conversations.id = messages.conversation_id"},
                    {"table": "insightmesh_users", "on": "conversations.user_id = insightmesh_users.id"}
                ]
            },
            {
                "database": "slack",
                "table": "slack_messages",
                "filters": {"thread_ts": "NOT NULL"},
                "group_by": "thread_ts"
            },
            {
                "elastic": "conversation_index",
                "query_fields": ["title", "summary", "tags"]
            }
        ]
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "notion", "webcat"]
    
    @property
    def aggregations(self) -> Dict[str, Any]:
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
    def contexts(self) -> List[Dict[str, Any]]:
        return [
            {
                "messages": {
                    "access": {"roles": ["analyst", "support", "admin"], "scopes": ["read", "write"]},
                    "permissions": {
                        "read": ["channel:history", "im:history", "mpim:history"],
                        "write": ["chat:write", "chat:write.public"]
                    }
                }
            },
            {
                "channels": {
                    "access": {"roles": ["member", "admin"], "scopes": ["read", "write"]},
                    "permissions": {
                        "read": ["channels:read", "groups:read"],
                        "write": ["channels:manage", "groups:write"]
                    }
                }
            }
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages", "channels"]
    
    @property
    def config(self) -> Dict[str, Any]:
        return {
            "base_url": "https://slack.com/api",
            "rate_limit": 50,
            "timeout": 30
        }

@tool("webcat", "Web search service for research and information gathering", "mcp")
class WebcatTool(BaseTool):
    @property
    def auth(self) -> str:
        return "none"
    
    @property
    def contexts(self) -> List[Dict[str, Any]]:
        return [
            {
                "messages": {
                    "access": {"roles": ["analyst", "researcher", "admin"], "scopes": ["read"]},
                    "use_cases": ["fact_checking", "context_enrichment"]
                }
            }
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages", "research"]
    
    @property
    def config(self) -> Dict[str, Any]:
        return {
            "rate_limit": 100,
            "timeout": 15,
            "max_results": 10
        }

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