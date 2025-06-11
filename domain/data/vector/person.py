"""
Vector database data object for Person.
"""

from typing import Dict, Any, List, Optional, Tuple
from .base import ElasticsearchVectorBase
import logging
import numpy as np

logger = logging.getLogger(__name__)


class VectorPerson(ElasticsearchVectorBase):
    """Vector database-specific person data object."""
    
    def __init__(self, 
                 vector_id: str,
                 embedding: List[float] = None,
                 metadata: Dict[str, Any] = None,
                 content: str = None):
        """Initialize VectorPerson."""
        super().__init__(vector_id, embedding, metadata, content)
        
        # Person-specific metadata
        self.name = self.metadata.get('name', '')
        self.email = self.metadata.get('email', '')
        self.title = self.metadata.get('title', '')
        self.department = self.metadata.get('department', '')
        self.skills = self.metadata.get('skills', [])
        self.bio = self.metadata.get('bio', '')
        
        # Vector-specific fields
        self.embedding_model = self.metadata.get('embedding_model', 'unknown')
        self.embedding_version = self.metadata.get('embedding_version', '1.0')
        self.last_updated = self.metadata.get('last_updated')
    
    @classmethod
    def from_person_data(cls, 
                        person_id: str,
                        name: str = None,
                        email: str = None,
                        title: str = None,
                        department: str = None,
                        skills: List[str] = None,
                        bio: str = None,
                        embedding: List[float] = None) -> 'VectorPerson':
        """Create VectorPerson from person data."""
        
        # Build content for embedding if not provided
        if not embedding:
            content_parts = [
                name or '',
                title or '',
                department or '',
                ' '.join(skills or []),
                bio or ''
            ]
            content = ' '.join(filter(None, content_parts))
        else:
            content = None
        
        metadata = {
            'name': name,
            'email': email,
            'title': title,
            'department': department,
            'skills': skills or [],
            'bio': bio,
            'source': 'person',
            'source_id': person_id
        }
        
        return cls(
            vector_id=person_id,
            embedding=embedding,
            metadata=metadata,
            content=content
        )
    
    def generate_embedding_content(self) -> str:
        """Generate content string for embedding generation."""
        content_parts = [
            f"Name: {self.name}" if self.name else "",
            f"Title: {self.title}" if self.title else "",
            f"Department: {self.department}" if self.department else "",
            f"Skills: {', '.join(self.skills)}" if self.skills else "",
            f"Bio: {self.bio}" if self.bio else ""
        ]
        return ' '.join(filter(None, content_parts))
    
    def find_similar_people(self, 
                           top_k: int = 10, 
                           threshold: float = 0.7,
                           department_filter: str = None,
                           skill_filter: List[str] = None,
                           index: str = "person_vectors") -> List[Tuple['VectorPerson', float]]:
        """Find people with similar embeddings."""
        filters = {}
        
        if department_filter:
            filters['metadata.department'] = department_filter
        
        if skill_filter:
            # For skills, we need a more complex filter
            # This would need to be adapted based on your vector DB implementation
            pass
        
        return self.find_similar(top_k, threshold, filters, index)
    
    def find_people_by_skills(self, 
                             target_skills: List[str],
                             top_k: int = 10,
                             index: str = "person_vectors") -> List[Tuple['VectorPerson', float]]:
        """Find people with similar skills using vector similarity."""
        if not self.embedding:
            return []
        
        # Create a temporary embedding for the target skills
        skills_content = f"Skills: {', '.join(target_skills)}"
        
        # In a real implementation, you'd generate an embedding for skills_content
        # For now, we'll use the existing embedding and filter by metadata
        filters = {}
        
        # Find people who have any of the target skills
        # This is a simplified approach - in practice you'd want more sophisticated matching
        return self.find_similar(top_k, 0.5, filters, index)
    
    def get_skill_clusters(self, 
                          skill_vectors: Dict[str, List[float]],
                          threshold: float = 0.8) -> Dict[str, List[str]]:
        """Group skills into clusters based on vector similarity."""
        if not self.embedding:
            return {}
        
        clusters = {}
        processed_skills = set()
        
        for skill, skill_embedding in skill_vectors.items():
            if skill in processed_skills:
                continue
            
            # Calculate similarity with this person's embedding
            similarity = self.cosine_similarity(skill_embedding)
            
            if similarity >= threshold:
                cluster_name = f"cluster_{len(clusters)}"
                clusters[cluster_name] = [skill]
                processed_skills.add(skill)
                
                # Find other similar skills
                for other_skill, other_embedding in skill_vectors.items():
                    if other_skill != skill and other_skill not in processed_skills:
                        skill_similarity = self.cosine_similarity(other_embedding)
                        if skill_similarity >= threshold:
                            clusters[cluster_name].append(other_skill)
                            processed_skills.add(other_skill)
        
        return clusters
    
    def calculate_role_similarity(self, other_person: 'VectorPerson') -> Dict[str, float]:
        """Calculate similarity scores across different dimensions."""
        similarities = {}
        
        # Vector similarity
        if self.embedding is not None and other_person.embedding is not None:
            similarities['vector_similarity'] = self.cosine_similarity(other_person.embedding)
        
        # Department similarity
        if self.department and other_person.department:
            similarities['department_match'] = 1.0 if self.department == other_person.department else 0.0
        
        # Title similarity (simplified - could use more sophisticated NLP)
        if self.title and other_person.title:
            title_words_self = set(self.title.lower().split())
            title_words_other = set(other_person.title.lower().split())
            if title_words_self and title_words_other:
                similarities['title_similarity'] = len(title_words_self & title_words_other) / len(title_words_self | title_words_other)
        
        # Skills overlap
        if self.skills and other_person.skills:
            skills_self = set(self.skills)
            skills_other = set(other_person.skills)
            if skills_self and skills_other:
                similarities['skills_overlap'] = len(skills_self & skills_other) / len(skills_self | skills_other)
        
        return similarities
    
    def get_expertise_vector(self) -> Optional[np.ndarray]:
        """Get a vector representing this person's expertise areas."""
        if not self.embedding:
            return None
        
        # In a more sophisticated implementation, this could:
        # 1. Weight the embedding by skills
        # 2. Combine multiple embeddings (bio, skills, recent messages)
        # 3. Use domain-specific embeddings
        
        return self.embedding
    
    def update_embedding(self, new_embedding: List[float], model_info: Dict[str, str] = None) -> bool:
        """Update the person's embedding with new vector data."""
        self.embedding = np.array(new_embedding)
        self.dimension = len(new_embedding)
        
        if model_info:
            self.embedding_model = model_info.get('model', self.embedding_model)
            self.embedding_version = model_info.get('version', self.embedding_version)
            self.metadata.update({
                'embedding_model': self.embedding_model,
                'embedding_version': self.embedding_version
            })
        
        # Update timestamp
        from datetime import datetime
        self.last_updated = datetime.utcnow().isoformat()
        self.metadata['last_updated'] = self.last_updated
        
        return True
    
    def get_recommended_connections(self, 
                                  exclude_departments: List[str] = None,
                                  min_similarity: float = 0.6,
                                  max_results: int = 5,
                                  index: str = "person_vectors") -> List[Tuple['VectorPerson', float, str]]:
        """Get recommended people to connect with based on complementary skills."""
        if not self.embedding:
            return []
        
        filters = {}
        if exclude_departments:
            # This would need to be implemented based on your vector DB's filter syntax
            pass
        
        # Find similar people
        similar_people = self.find_similar(max_results * 2, min_similarity, filters, index)
        
        recommendations = []
        for person, similarity in similar_people:
            # Calculate recommendation reason
            reason = self._get_recommendation_reason(person, similarity)
            recommendations.append((person, similarity, reason))
        
        return recommendations[:max_results]
    
    def _get_recommendation_reason(self, other_person: 'VectorPerson', similarity: float) -> str:
        """Generate a reason for recommending this connection."""
        reasons = []
        
        if hasattr(other_person, 'department') and other_person.department == self.department:
            reasons.append("same department")
        
        if hasattr(other_person, 'skills') and self.skills:
            common_skills = set(self.skills) & set(other_person.skills or [])
            if common_skills:
                reasons.append(f"shared skills: {', '.join(list(common_skills)[:2])}")
        
        if similarity > 0.8:
            reasons.append("high similarity")
        elif similarity > 0.7:
            reasons.append("good match")
        
        return "; ".join(reasons) if reasons else "potential collaboration"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert VectorPerson to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            "name": self.name,
            "email": self.email,
            "title": self.title,
            "department": self.department,
            "skills": self.skills,
            "bio": self.bio,
            "embedding_model": self.embedding_model,
            "embedding_version": self.embedding_version,
            "last_updated": self.last_updated
        })
        return base_dict 