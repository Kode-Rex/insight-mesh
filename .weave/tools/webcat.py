import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import tool, BaseTool
from typing import Dict, List, Any

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
            },
            {
                "research": {
                    "access": {"roles": ["analyst", "researcher"], "scopes": ["read"]},
                    "use_cases": ["competitive_analysis", "market_research"]
                }
            }
        ]
    
    @property
    def domains(self) -> List[str]:
        return ["person", "messages", "research"]
    
    @property
    def config(self) -> Dict[str, Any]:
        return {
            "base_url": "TODO: look this up as per the `service list` command",
            "rate_limit": 100,
            "timeout": 15,
            "max_results": 10
        }
    
    @property
    def permissions(self) -> Dict[str, Any]:
        return {
            "default": "read",
            "allowed_domains": ["*"],
            "blocked_domains": []
        }
    
    @property
    def filters(self) -> Dict[str, Any]:
        return {
            "safe_search": True,
            "language": "en"
        } 