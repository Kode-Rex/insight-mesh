import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import context, BaseContext
from typing import Dict, List, Any

@context("conversations", "Threaded conversations across platforms with full message history")
class ConversationsContext(BaseContext):
    @property
    def domains(self) -> List[str]:
        return ["messages", "person", "channels"]
    
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
    def permissions(self) -> Dict[str, Any]:
        return {
            "default": "read",
            "roles": ["participant", "observer", "admin"],
            "scopes": {
                "participant": "own_conversations",
                "observer": "public_conversations",
                "admin": "all_conversations"
            }
        }
    
    @property
    def aggregations(self) -> Dict[str, str]:
        return {
            "message_count": "COUNT(messages.id)",
            "last_activity": "MAX(messages.created_at)",
            "participants": "ARRAY_AGG(DISTINCT users.name)"
        }
    
    @property
    def filters(self) -> Dict[str, str]:
        return {
            "active_only": "last_activity > NOW() - INTERVAL '30 days'",
            "user_scope": "$user.id"
        } 