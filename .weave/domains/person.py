import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import domain, BaseDomain
from typing import Dict, List, Any

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