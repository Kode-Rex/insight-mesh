import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import domain, BaseDomain
from typing import Dict, List, Any

@domain("channels", "Communication channels across different platforms (Slack, Teams, etc.)")
class ChannelsDomain(BaseDomain):
    @property
    def schemas(self) -> Dict[str, Any]:
        return {
            "sql": {
                "slack": "slack_channels"
            },
            "neo4j": "(:Channel)",
            "elastic": "channel_index"
        }
    
    @property
    def contexts(self) -> List[str]:
        return ["messages", "members", "activity"]
    
    @property
    def sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "database": "slack",
                "table": "slack_channels",
                "filters": {"is_archived": False}
            },
            {
                "elastic": "channel_index",
                "query_fields": ["name", "purpose", "topic"]
            }
        ]
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "teams"]
    
    @property
    def permissions(self) -> Dict[str, Any]:
        return {
            "default": "read",
            "roles": ["member", "admin"],
            "scopes": {
                "member": "joined_channels_only",
                "admin": "all_channels"
            }
        }
    
    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return [
            {"domain": "messages", "type": "has_many", "foreign_key": "channel_id"},
            {"domain": "person", "type": "has_many", "through": "channel_members"}
        ] 