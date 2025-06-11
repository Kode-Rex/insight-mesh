import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import tool, BaseTool
from typing import Dict, List, Any

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
            },
            {
                "person": {
                    "access": {"roles": ["admin"], "scopes": ["read"]},
                    "permissions": {
                        "read": ["users:read", "users:read.email"]
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
    
    @property
    def filters(self) -> Dict[str, Any]:
        return {
            "user_scope": "$user.slack_id",
            "team_scope": "$team.id"
        } 