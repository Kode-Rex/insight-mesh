"""
Person domain model.

Represents people in the system, with relationships to messages, tasks, and channels.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PersonSchema:
    """Schema definitions for Person across different storage systems"""
    sql_insightmesh: str = "insightmesh_users"
    sql_slack: str = "slack_users"
    neo4j: str = "(:Person)"
    elastic: str = "person_index"


@dataclass
class PersonPermissions:
    """Permission configuration for Person domain"""
    default: str = "read"
    roles: List[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ["analyst", "support", "admin"]


@dataclass
class PersonRelationship:
    """Represents a relationship between Person and other domains"""
    domain: str
    type: str
    foreign_key: Optional[str] = None
    through: Optional[str] = None


class Person:
    """
    Person domain model representing people in the system.
    
    This model encapsulates the business logic and relationships for people,
    including their connections to messages, channels, and other entities.
    """
    
    def __init__(self, 
                 id: str,
                 name: Optional[str] = None,
                 email: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 _data_objects: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.email = email
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        
        # Store references to underlying data objects from different sources
        self._data_objects = _data_objects or {}
        
        # Define schema mappings
        self.schema = PersonSchema()
        
        # Define permissions
        self.permissions = PersonPermissions()
        
        # Define relationships
        self.relationships = [
            PersonRelationship(
                domain="messages",
                type="has_many",
                foreign_key="user_id"
            ),
            PersonRelationship(
                domain="channels",
                type="belongs_to_many",
                through="channel_members"
            )
        ]
        
        # Context areas this domain participates in
        self.contexts = ["messages", "tasks", "channels"]
    
    @classmethod
    def from_data_objects(cls, 
                         slack_user=None, 
                         insightmesh_user=None, 
                         email_contact=None,
                         graph_person=None,
                         search_person=None,
                         vector_person=None) -> 'Person':
        """
        Create a Person domain object from multiple underlying data objects.
        
        This method demonstrates how a domain object can unify data from
        multiple sources (Slack user, InsightMesh user, email contact, etc.)
        """
        # Determine primary identity (prefer InsightMesh, fallback to Slack)
        primary_id = None
        primary_name = None
        primary_email = None
        
        if insightmesh_user:
            primary_id = insightmesh_user.id
            primary_name = insightmesh_user.name
            primary_email = insightmesh_user.email
        elif slack_user:
            primary_id = slack_user.id
            primary_name = getattr(slack_user, 'real_name', None) or getattr(slack_user, 'display_name', None)
            primary_email = getattr(slack_user, 'email', None)
        elif email_contact:
            primary_id = email_contact.get('email', '')
            primary_name = email_contact.get('name', '')
            primary_email = email_contact.get('email', '')
        
        # Merge metadata from all sources
        metadata = {}
        if slack_user:
            metadata['slack'] = {
                'id': slack_user.id,
                'display_name': getattr(slack_user, 'display_name', None),
                'real_name': getattr(slack_user, 'real_name', None),
                'title': getattr(slack_user, 'title', None),
                'status': getattr(slack_user, 'status', None)
            }
        if insightmesh_user:
            metadata['insightmesh'] = {
                'id': insightmesh_user.id,
                'openwebui_id': getattr(insightmesh_user, 'openwebui_id', None),
                'is_active': getattr(insightmesh_user, 'is_active', None)
            }
        if email_contact:
            metadata['email'] = email_contact
        
        return cls(
            id=primary_id,
            name=primary_name,
            email=primary_email,
            metadata=metadata,
            _data_objects={
                'slack': slack_user,
                'insightmesh': insightmesh_user,
                'email': email_contact,
                'graph': graph_person,
                'search': search_person,
                'vector': vector_person
            }
        )
    
    @classmethod
    def from_slack_user(cls, slack_user) -> 'Person':
        """Create a Person from a Slack user data object."""
        return cls.from_data_objects(slack_user=slack_user)
    
    @classmethod
    def from_insightmesh_user(cls, im_user) -> 'Person':
        """Create a Person from an InsightMesh user data object."""
        return cls.from_data_objects(insightmesh_user=im_user)
    
    def get_messages(self) -> List['Message']:
        """Get all messages associated with this person"""
        # This would be implemented to fetch from the appropriate data layer
        # and use Message.get_for_user() to aggregate across sources
        pass
    
    def get_channels(self) -> List['Channel']:
        """Get all channels this person belongs to"""
        # This would be implemented to fetch from the appropriate data layer
        pass
    
    def get_data_object(self, source: str):
        """Get the underlying data object for a specific source"""
        return self._data_objects.get(source)
    
    def has_data_from_source(self, source: str) -> bool:
        """Check if person has data from a specific source"""
        return source in self._data_objects and self._data_objects[source] is not None
    
    def get_all_sources(self) -> List[str]:
        """Get list of all sources this person has data from"""
        return [source for source, data in self._data_objects.items() if data is not None]
    
    def has_permission(self, action: str, role: str = None) -> bool:
        """Check if person has permission for a given action"""
        if role and role in self.permissions.roles:
            return True
        return action == self.permissions.default
    
    def get_schema_for_storage(self, storage_type: str) -> str:
        """Get the appropriate schema/table name for a storage system"""
        schema_map = {
            'sql_insightmesh': self.schema.sql_insightmesh,
            'sql_slack': self.schema.sql_slack,
            'neo4j': self.schema.neo4j,
            'elastic': self.schema.elastic
        }
        return schema_map.get(storage_type, self.schema.sql_insightmesh)
    
    def get_relationship_network(self, depth: int = 2) -> Dict[str, Any]:
        """Get person's relationship network from graph database."""
        graph_person = self.get_data_object('graph')
        if graph_person:
            return {
                'colleagues': graph_person.get_colleagues(depth),
                'communication_network': graph_person.get_communication_network(),
                'expertise_areas': graph_person.get_expertise_areas(),
                'influence_score': graph_person.get_influence_score()
            }
        return {}
    
    def find_similar_people(self, threshold: float = 0.7, method: str = 'vector') -> List[Dict[str, Any]]:
        """Find similar people using vector similarity or graph analysis."""
        if method == 'vector':
            vector_person = self.get_data_object('vector')
            if vector_person:
                similar = vector_person.find_similar_people(threshold=threshold)
                return [{'person_id': p.id, 'similarity': score, 'method': 'vector'} 
                       for p, score in similar]
        
        elif method == 'graph':
            graph_person = self.get_data_object('graph')
            if graph_person:
                similar = graph_person.find_similar_people(threshold)
                return [{'person_id': p['other']['id'], 'similarity': p['similarity_score'], 'method': 'graph'} 
                       for p in similar]
        
        return []
    
    def search_mentions(self, query: str) -> List[Dict[str, Any]]:
        """Search for mentions of this person across documents."""
        search_person = self.get_data_object('search')
        if search_person:
            # Search for documents mentioning this person
            search_query = f'"{self.name}" OR "{self.email}"'
            if self.metadata.get('slack', {}).get('display_name'):
                search_query += f' OR "{self.metadata["slack"]["display_name"]}"'
            
            results = search_person.search(search_query)
            return results.get('hits', {}).get('hits', [])
        return []
    
    def get_expertise_recommendations(self, skill_area: str = None) -> List[Dict[str, Any]]:
        """Get people recommendations based on expertise and connections."""
        recommendations = []
        
        # Get vector-based recommendations
        vector_person = self.get_data_object('vector')
        if vector_person:
            vector_recs = vector_person.get_recommended_connections()
            recommendations.extend([
                {
                    'person_id': person.id,
                    'similarity': score,
                    'reason': reason,
                    'method': 'vector_similarity'
                }
                for person, score, reason in vector_recs
            ])
        
        # Get graph-based recommendations
        graph_person = self.get_data_object('graph')
        if graph_person:
            colleagues = graph_person.get_colleagues()
            recommendations.extend([
                {
                    'person_id': colleague['colleague']['id'],
                    'similarity': colleague['connection_strength'] / 10.0,  # Normalize
                    'reason': f"shared contexts: {', '.join(colleague['shared_contexts'])}",
                    'method': 'graph_connections'
                }
                for colleague in colleagues[:5]
            ])
        
        return recommendations
    
    def get_activity_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get insights about person's activity across different systems."""
        insights = {}
        
        # Graph-based activity
        graph_person = self.get_data_object('graph')
        if graph_person:
            insights['graph_activity'] = graph_person.get_activity_timeline(days)
        
        # Search-based activity stats
        search_person = self.get_data_object('search')
        if search_person and hasattr(search_person, 'message_count'):
            insights['search_stats'] = {
                'message_count': search_person.message_count,
                'channel_count': search_person.channel_count,
                'last_activity': search_person.last_activity
            }
        
        return insights
    
    def update_all_data_objects(self, updates: Dict[str, Any]) -> bool:
        """Update person data across all storage systems."""
        success = True
        
        # Update graph data
        graph_person = self.get_data_object('graph')
        if graph_person:
            for key, value in updates.items():
                if hasattr(graph_person, key):
                    setattr(graph_person, key, value)
            success &= graph_person.save()
        
        # Update search data
        search_person = self.get_data_object('search')
        if search_person:
            search_doc = search_person.to_elasticsearch_doc()
            search_doc.update(updates)
            success &= search_person.index_document(search_person.index, search_person.id, search_doc)
        
        # Update vector data if embedding-related
        vector_person = self.get_data_object('vector')
        if vector_person and any(key in ['bio', 'title', 'skills'] for key in updates.keys()):
            # Regenerate content for embedding
            vector_person.content = vector_person.generate_embedding_content()
            # Note: In practice, you'd regenerate the embedding here
            success &= vector_person.save()
        
        return success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert person to dictionary representation"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'contexts': self.contexts
        }
    
    def __repr__(self) -> str:
        return f"Person(id='{self.id}', name='{self.name}', email='{self.email}')" 