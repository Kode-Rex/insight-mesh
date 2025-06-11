import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from weave.domains import domain, BaseDomain, Permission, Relationship, RelationshipType
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