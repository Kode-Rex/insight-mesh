"""
Domain-Context-Tool loader for Weave.
Bridges YAML domain definitions with existing SQLAlchemy models.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DomainConfig:
    """Domain configuration from YAML"""
    name: str
    description: str
    schemas: Dict[str, Any]
    contexts: List[str]
    tools: List[str]
    permissions: Dict[str, Any]
    relationships: List[Dict[str, Any]]

@dataclass
class ContextConfig:
    """Context configuration from YAML"""
    name: str
    description: str
    domains: List[str]
    sources: List[Dict[str, Any]]
    tools: List[str]
    permissions: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    aggregations: Optional[Dict[str, Any]] = None

@dataclass
class ToolConfig:
    """Tool configuration from YAML"""
    name: str
    type: str
    description: str
    auth: str
    contexts: List[Dict[str, Any]]
    domains: List[str]
    config: Dict[str, Any]
    permissions: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None

class DomainLoader:
    """Loads and manages domain-context-tool configurations"""
    
    def __init__(self, weave_path: str = ".weave"):
        self.weave_path = Path(weave_path)
        self.domains: Dict[str, DomainConfig] = {}
        self.contexts: Dict[str, ContextConfig] = {}
        self.tools: Dict[str, ToolConfig] = {}
        
    def load_all(self):
        """Load all domain, context, and tool configurations"""
        self.load_domains()
        self.load_contexts()
        self.load_tools()
        
    def load_domains(self):
        """Load domain configurations from YAML files"""
        domains_path = self.weave_path / "domains"
        if not domains_path.exists():
            logger.warning(f"Domains path {domains_path} does not exist")
            return
            
        for yaml_file in domains_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    
                domain = DomainConfig(
                    name=config['domain'],
                    description=config['description'],
                    schemas=config.get('schemas', {}),
                    contexts=config.get('contexts', []),
                    tools=config.get('tools', []),
                    permissions=config.get('permissions', {}),
                    relationships=config.get('relationships', [])
                )
                
                self.domains[domain.name] = domain
                logger.info(f"Loaded domain: {domain.name}")
                
            except Exception as e:
                logger.error(f"Failed to load domain from {yaml_file}: {e}")
                
    def load_contexts(self):
        """Load context configurations from YAML files"""
        contexts_path = self.weave_path / "contexts"
        if not contexts_path.exists():
            logger.warning(f"Contexts path {contexts_path} does not exist")
            return
            
        for yaml_file in contexts_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    
                context = ContextConfig(
                    name=config['context'],
                    description=config['description'],
                    domains=config.get('domains', []),
                    sources=config.get('sources', []),
                    tools=config.get('tools', []),
                    permissions=config.get('permissions', {}),
                    filters=config.get('filters'),
                    aggregations=config.get('aggregations')
                )
                
                self.contexts[context.name] = context
                logger.info(f"Loaded context: {context.name}")
                
            except Exception as e:
                logger.error(f"Failed to load context from {yaml_file}: {e}")
                
    def load_tools(self):
        """Load tool configurations from YAML files"""
        tools_path = self.weave_path / "tools"
        if not tools_path.exists():
            logger.warning(f"Tools path {tools_path} does not exist")
            return
            
        for yaml_file in tools_path.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    
                tool = ToolConfig(
                    name=config['tool'],
                    type=config['type'],
                    description=config['description'],
                    auth=config['auth'],
                    contexts=config.get('contexts', []),
                    domains=config.get('domains', []),
                    config=config.get('config', {}),
                    permissions=config.get('permissions', {}),
                    filters=config.get('filters')
                )
                
                self.tools[tool.name] = tool
                logger.info(f"Loaded tool: {tool.name}")
                
            except Exception as e:
                logger.error(f"Failed to load tool from {yaml_file}: {e}")
                
    def get_domain_schemas(self, domain_name: str) -> Dict[str, Any]:
        """Get schema mappings for a domain"""
        if domain_name not in self.domains:
            return {}
        return self.domains[domain_name].schemas
        
    def get_context_sources(self, context_name: str) -> List[Dict[str, Any]]:
        """Get data sources for a context"""
        if context_name not in self.contexts:
            return []
        return self.contexts[context_name].sources
        
    def get_tool_permissions(self, tool_name: str, context_name: str) -> Dict[str, Any]:
        """Get tool permissions for a specific context"""
        if tool_name not in self.tools:
            return {}
            
        tool = self.tools[tool_name]
        for context_config in tool.contexts:
            if isinstance(context_config, dict) and context_name in context_config:
                return context_config[context_name].get('permissions', {})
        return {}
        
    def inject_context(self, domain: str, context: str, user_id: str) -> Dict[str, Any]:
        """Inject context for domain-aware agent execution"""
        result = {
            'domain': domain,
            'context': context,
            'user_id': user_id,
            'schemas': {},
            'sources': [],
            'tools': [],
            'permissions': {}
        }
        
        # Get domain schemas
        if domain in self.domains:
            result['schemas'] = self.get_domain_schemas(domain)
            
        # Get context sources
        if context in self.contexts:
            result['sources'] = self.get_context_sources(context)
            
        # Get available tools for this domain/context
        for tool_name, tool_config in self.tools.items():
            if domain in tool_config.domains:
                result['tools'].append({
                    'name': tool_name,
                    'type': tool_config.type,
                    'permissions': self.get_tool_permissions(tool_name, context)
                })
                
        return result
        
    def list_domains(self) -> List[str]:
        """List all available domains"""
        return list(self.domains.keys())
        
    def list_contexts(self, domain: str = None) -> List[str]:
        """List all contexts, optionally filtered by domain"""
        if domain and domain in self.domains:
            return self.domains[domain].contexts
        return list(self.contexts.keys())
        
    def list_tools(self, domain: str = None) -> List[str]:
        """List all tools, optionally filtered by domain"""
        if domain:
            return [name for name, tool in self.tools.items() 
                   if domain in tool.domains]
        return list(self.tools.keys())

# Global loader instance
_loader = None

def get_loader() -> DomainLoader:
    """Get the global domain loader instance"""
    global _loader
    if _loader is None:
        _loader = DomainLoader()
        _loader.load_all()
    return _loader 