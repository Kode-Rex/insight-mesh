"""
Agent definitions using Python decorators and classes.
Replaces YAML-based agent configuration with code.
"""

from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from domains import get_domain, get_context, get_tool

# Agent registry
_agents = {}

def agent(name: str, domain: str, context: str, description: str = ""):
    """Decorator to register an agent class"""
    def decorator(cls):
        cls._agent_name = name
        cls._domain = domain
        cls._context = context
        cls._description = description
        _agents[name] = cls
        return cls
    return decorator

class BaseAgent(ABC):
    """Base class for all agents"""
    
    @property
    def description(self) -> str:
        """Agent description"""
        return getattr(self, '_description', '')
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.domain_context = None
        if hasattr(self, '_domain') and hasattr(self, '_context'):
            self.domain_context = self.inject_context()
    
    @property
    @abstractmethod
    def goal(self) -> str:
        """The agent's primary goal"""
        pass
    
    @property
    def tools(self) -> List[str]:
        """Tools available to this agent (from domain context)"""
        if self.domain_context:
            return [tool['name'] for tool in self.domain_context.get('tools', [])]
        return []
    
    @property
    def execution_config(self) -> Dict[str, Any]:
        """Execution configuration"""
        return {
            "timeout": 300,
            "retry": 3,
            "cache": True,
            "memory_limit": "512Mi"
        }
    
    @property
    def observability(self) -> Dict[str, Any]:
        """Observability configuration"""
        return {
            "trace": True,
            "metrics": True,
            "logs": "info"
        }
    
    @property
    def environment(self) -> Dict[str, str]:
        """Environment variables"""
        return {
            "MODEL": "gpt-4",
            "MAX_TOKENS": "2000",
            "TEMPERATURE": "0.7"
        }
    
    def inject_context(self) -> Dict[str, Any]:
        """Inject domain context for this agent"""
        if not hasattr(self, '_domain') or not hasattr(self, '_context'):
            return {}
        
        # Get domain and context instances
        domain = get_domain(self._domain)
        context = get_context(self._context)
        
        if not domain:
            return {}
        
        # Build context similar to domain_loader
        result = {
            'domain': self._domain,
            'context': self._context,
            'user_id': self.user_id,
            'schemas': domain.schemas,
            'sources': context.sources if context else [],
            'tools': [],
            'permissions': domain.permissions
        }
        
        # Get available tools for this domain
        for tool_name in domain.tools:
            tool = get_tool(tool_name)
            if tool and self._domain in tool.domains:
                result['tools'].append({
                    'name': tool_name,
                    'type': tool._tool_type,
                    'permissions': self._get_tool_permissions(tool, self._context)
                })
        
        return result
    
    def _get_tool_permissions(self, tool, context_name: str) -> Dict[str, Any]:
        """Get tool permissions for specific context"""
        for context_config in tool.contexts:
            if isinstance(context_config, dict) and context_name in context_config:
                return context_config[context_name].get('permissions', {})
        return {}
    
    @abstractmethod
    async def execute(self, query: str, **kwargs) -> str:
        """Execute the agent with given input"""
        pass

# Agent definitions
@agent("customer-support", "person", "messages", 
       "Resolve customer issues using conversation history and available tools")
class CustomerSupportAgent(BaseAgent):
    @property
    def goal(self) -> str:
        return """Help customers resolve issues by:
        1. Understanding their problem from conversation history
        2. Searching for solutions using available tools
        3. Providing clear, actionable responses"""
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute customer support logic"""
        # Access domain context
        schemas = self.domain_context.get('schemas', {})
        tools = self.domain_context.get('tools', [])
        
        # Example logic
        if self._is_technical_issue(query):
            return await self._handle_technical_issue(query)
        elif self._is_billing_issue(query):
            return await self._handle_billing_issue(query)
        else:
            return await self._handle_general_support(query)
    
    def _is_technical_issue(self, query: str) -> bool:
        """Classify if this is a technical issue"""
        technical_keywords = ["error", "bug", "crash", "not working", "broken"]
        return any(keyword in query.lower() for keyword in technical_keywords)
    
    def _is_billing_issue(self, query: str) -> bool:
        """Classify if this is a billing issue"""
        billing_keywords = ["payment", "billing", "invoice", "charge", "refund"]
        return any(keyword in query.lower() for keyword in billing_keywords)
    
    async def _handle_technical_issue(self, query: str) -> str:
        """Handle technical support issues"""
        return f"Technical issue detected: {query}. Escalating to technical team."
    
    async def _handle_billing_issue(self, query: str) -> str:
        """Handle billing support issues"""
        return f"Billing issue detected: {query}. Checking account status."
    
    async def _handle_general_support(self, query: str) -> str:
        """Handle general support issues"""
        return f"General support query: {query}. Searching knowledge base."

@agent("onboarding-workflow", "person", "messages",
       "Complete customer onboarding process with multiple steps")
class OnboardingWorkflowAgent(BaseAgent):
    @property
    def goal(self) -> str:
        return "Guide new customers through the complete onboarding process"
    
    @property
    def execution_config(self) -> Dict[str, Any]:
        return {
            "timeout": 900,  # Longer for workflows
            "retry": 3,
            "cache": True,
            "memory_limit": "1Gi"
        }
    
    async def execute(self, email: str, name: str, **kwargs) -> str:
        """Execute onboarding workflow"""
        steps = []
        
        # Step 1: Create account
        account_result = await self._create_account(email, name)
        steps.append(f"Account created: {account_result}")
        
        # Step 2: Send welcome email
        if account_result:
            welcome_result = await self._send_welcome_email(email)
            steps.append(f"Welcome email sent: {welcome_result}")
        
        # Step 3: Setup initial preferences
        prefs_result = await self._setup_preferences(email)
        steps.append(f"Preferences setup: {prefs_result}")
        
        return f"Onboarding completed: {'; '.join(steps)}"
    
    async def _create_account(self, email: str, name: str) -> str:
        """Create user account"""
        # Access domain schemas to know which tables to use
        schemas = self.domain_context.get('schemas', {})
        sql_schemas = schemas.get('sql', {})
        
        # Would create account in insightmesh_users table
        return f"Account created for {name} ({email}) in {sql_schemas.get('insightmesh', 'unknown')}"
    
    async def _send_welcome_email(self, email: str) -> str:
        """Send welcome email"""
        return f"Welcome email sent to {email}"
    
    async def _setup_preferences(self, email: str) -> str:
        """Setup initial user preferences"""
        return f"Default preferences set for {email}"

@agent("slack-responder", "messages", "conversations",
       "Automatically respond to Slack messages based on content")
class SlackResponderAgent(BaseAgent):
    @property
    def goal(self) -> str:
        return "Automatically respond to Slack messages with appropriate actions"
    
    @property
    def environment(self) -> Dict[str, str]:
        return {
            "MODEL": "gpt-3.5-turbo",  # Faster for real-time responses
            "MAX_TOKENS": "500",
            "TEMPERATURE": "0.3"
        }
    
    async def execute(self, message: str, channel: str, user: str, **kwargs) -> str:
        """Execute Slack response logic"""
        # Check tool permissions
        slack_tool = next((t for t in self.domain_context.get('tools', []) if t['name'] == 'slack'), None)
        if not slack_tool:
            return "Slack tool not available"
        
        # Check if we have write permissions
        permissions = slack_tool.get('permissions', {})
        if 'chat:write' not in permissions.get('write', []):
            return "No write permissions for Slack"
        
        # Generate response based on message content
        if '@support' in message:
            return await self._escalate_to_support(message, user)
        elif '?' in message:
            return await self._answer_question(message)
        else:
            return await self._acknowledge_message(message)
    
    async def _escalate_to_support(self, message: str, user: str) -> str:
        """Escalate message to support team"""
        return f"Support request from {user}: {message}. Notifying support team."
    
    async def _answer_question(self, message: str) -> str:
        """Answer a question"""
        return f"Question detected: {message}. Searching for answer..."
    
    async def _acknowledge_message(self, message: str) -> str:
        """Acknowledge a general message"""
        return f"Message acknowledged: {message}"

# Registry access functions
def get_agent(name: str) -> Optional[type]:
    """Get agent class by name"""
    return _agents.get(name)

def list_agents() -> List[str]:
    """List all registered agents"""
    return list(_agents.keys())

def get_all_agents() -> Dict[str, BaseAgent]:
    """Get all registered agents"""
    return {name: cls for name, cls in _agents.items()}

def create_agent(name: str, user_id: str = None) -> Optional[BaseAgent]:
    """Create agent instance by name"""
    agent_cls = _agents.get(name)
    return agent_cls(user_id=user_id) if agent_cls else None

# Context injection function (replaces domain_loader)
def inject_context(domain: str, context: str, user_id: str) -> Dict[str, Any]:
    """Inject context for domain-aware execution"""
    domain_obj = get_domain(domain)
    context_obj = get_context(context)
    
    if not domain_obj:
        return {}
    
    result = {
        'domain': domain,
        'context': context,
        'user_id': user_id,
        'schemas': domain_obj.schemas,
        'sources': context_obj.sources if context_obj else [],
        'tools': [],
        'permissions': domain_obj.permissions
    }
    
    # Get available tools for this domain
    for tool_name in domain_obj.tools:
        tool = get_tool(tool_name)
        if tool and domain in tool.domains:
            result['tools'].append({
                'name': tool_name,
                'type': tool._tool_type,
                'permissions': _get_tool_permissions(tool, context)
            })
    
    return result

def _get_tool_permissions(tool, context_name: str) -> Dict[str, Any]:
    """Get tool permissions for specific context"""
    for context_config in tool.contexts:
        if isinstance(context_config, dict) and context_name in context_config:
            return context_config[context_name].get('permissions', {})
    return {} 