import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import domain, BaseDomain
from typing import Dict, List, Any

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
    def sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "database": "slack",
                "table": "slack_messages",
                "filters": {"user_id": "$person.id"}
            },
            {
                "database": "insightmesh",
                "table": "messages",
                "filters": {"user_id": "$person.id"}
            },
            {
                "elastic": "message_index",
                "query_fields": ["content", "subject", "body"]
            }
        ]
    
    @property
    def tools(self) -> List[str]:
        return ["slack", "gmail", "notion"]
    
    @property
    def permissions(self) -> Dict[str, Any]:
        return {
            "default": "read",
            "roles": ["analyst", "support"],
            "scopes": {
                "user": "own_messages_only",
                "admin": "all_messages"
            }
        }
    
    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return [
            {"domain": "person", "type": "belongs_to", "foreign_key": "user_id"},
            {"domain": "channels", "type": "belongs_to", "foreign_key": "channel_id"}
        ] 