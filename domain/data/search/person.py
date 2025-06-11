"""
Elasticsearch search data object for Person.
"""

from typing import Dict, Any, List, Optional
from .base import SearchBase
import logging

logger = logging.getLogger(__name__)


class SearchPerson(SearchBase):
    """Elasticsearch-specific person data object."""
    
    def __init__(self, doc_data: Dict[str, Any], index_name: str = "people"):
        """Initialize SearchPerson from Elasticsearch document data."""
        super().__init__(doc_data, index_name)
        
        # Person-specific fields from source
        self.name = self.source.get('name', '')
        self.email = self.source.get('email', '')
        self.display_name = self.source.get('display_name', '')
        self.title = self.source.get('title', '')
        self.department = self.source.get('department', '')
        self.bio = self.source.get('bio', '')
        self.skills = self.source.get('skills', [])
        self.location = self.source.get('location', '')
        
        # Communication patterns
        self.message_count = self.source.get('message_count', 0)
        self.channel_count = self.source.get('channel_count', 0)
        self.last_activity = self.source.get('last_activity')
        
        # Derived fields for search
        self.full_text = self._build_full_text()
    
    def _build_full_text(self) -> str:
        """Build full-text search content from all person fields."""
        text_parts = [
            self.name,
            self.display_name,
            self.email,
            self.title,
            self.department,
            self.bio,
            ' '.join(self.skills) if self.skills else '',
            self.location
        ]
        return ' '.join(filter(None, text_parts))
    
    @classmethod
    def create_index_mapping(cls) -> Dict[str, Any]:
        """Create Elasticsearch mapping for person index."""
        return {
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "email": {
                        "type": "keyword"
                    },
                    "display_name": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "department": {
                        "type": "keyword"
                    },
                    "bio": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "skills": {
                        "type": "keyword"
                    },
                    "location": {
                        "type": "keyword"
                    },
                    "message_count": {
                        "type": "integer"
                    },
                    "channel_count": {
                        "type": "integer"
                    },
                    "last_activity": {
                        "type": "date"
                    },
                    "full_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    },
                    "meta": {
                        "type": "object",
                        "enabled": False
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "person_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"]
                        }
                    }
                }
            }
        }
    
    def search_by_name(self, query: str, fuzzy: bool = True) -> Dict[str, Any]:
        """Search for people by name with optional fuzzy matching."""
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "name": {
                                    "query": query,
                                    "boost": 3.0,
                                    "fuzziness": "AUTO" if fuzzy else 0
                                }
                            }
                        },
                        {
                            "match": {
                                "display_name": {
                                    "query": query,
                                    "boost": 2.0,
                                    "fuzziness": "AUTO" if fuzzy else 0
                                }
                            }
                        },
                        {
                            "wildcard": {
                                "email": f"*{query.lower()}*"
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "name": {},
                    "display_name": {},
                    "email": {}
                }
            }
        }
        
        return self.search(search_query, index=self.index)
    
    def search_by_skills(self, skills: List[str]) -> Dict[str, Any]:
        """Search for people by skills."""
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {"terms": {"skills": skills}},
                        {
                            "multi_match": {
                                "query": " ".join(skills),
                                "fields": ["bio^2", "title", "full_text"],
                                "type": "best_fields"
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "aggs": {
                "related_skills": {
                    "terms": {
                        "field": "skills",
                        "size": 20
                    }
                },
                "departments": {
                    "terms": {
                        "field": "department",
                        "size": 10
                    }
                }
            }
        }
        
        return self.search(search_query, index=self.index)
    
    def search_by_department(self, department: str) -> Dict[str, Any]:
        """Search for people in a specific department."""
        search_query = {
            "query": {
                "term": {
                    "department": department
                }
            },
            "sort": [
                {"message_count": {"order": "desc"}},
                {"name.keyword": {"order": "asc"}}
            ]
        }
        
        return self.search(search_query, index=self.index)
    
    def search_active_people(self, days: int = 30) -> Dict[str, Any]:
        """Search for people active within specified days."""
        search_query = {
            "query": {
                "range": {
                    "last_activity": {
                        "gte": f"now-{days}d"
                    }
                }
            },
            "sort": [
                {"last_activity": {"order": "desc"}},
                {"message_count": {"order": "desc"}}
            ]
        }
        
        return self.search(search_query, index=self.index)
    
    def get_department_stats(self) -> Dict[str, Any]:
        """Get statistics about people by department."""
        search_query = {
            "size": 0,
            "aggs": {
                "departments": {
                    "terms": {
                        "field": "department",
                        "size": 50
                    },
                    "aggs": {
                        "avg_messages": {
                            "avg": {
                                "field": "message_count"
                            }
                        },
                        "total_messages": {
                            "sum": {
                                "field": "message_count"
                            }
                        },
                        "active_count": {
                            "filter": {
                                "range": {
                                    "last_activity": {
                                        "gte": "now-30d"
                                    }
                                }
                            }
                        }
                    }
                },
                "skills_distribution": {
                    "terms": {
                        "field": "skills",
                        "size": 100
                    }
                }
            }
        }
        
        return self.search(search_query, index=self.index)
    
    def find_similar_people(self, similarity_fields: List[str] = None) -> Dict[str, Any]:
        """Find people similar to this person based on specified fields."""
        similarity_fields = similarity_fields or ["title", "department", "skills"]
        
        should_clauses = []
        
        if "title" in similarity_fields and self.title:
            should_clauses.append({
                "match": {
                    "title": {
                        "query": self.title,
                        "boost": 2.0
                    }
                }
            })
        
        if "department" in similarity_fields and self.department:
            should_clauses.append({
                "term": {
                    "department": {
                        "value": self.department,
                        "boost": 3.0
                    }
                }
            })
        
        if "skills" in similarity_fields and self.skills:
            should_clauses.append({
                "terms": {
                    "skills": self.skills,
                    "boost": 1.5
                }
            })
        
        search_query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "must_not": [
                        {"term": {"_id": self.id}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 10
        }
        
        return self.search(search_query, index=self.index)
    
    def to_elasticsearch_doc(self) -> Dict[str, Any]:
        """Convert SearchPerson to Elasticsearch document format."""
        return {
            "name": self.name,
            "email": self.email,
            "display_name": self.display_name,
            "title": self.title,
            "department": self.department,
            "bio": self.bio,
            "skills": self.skills,
            "location": self.location,
            "message_count": self.message_count,
            "channel_count": self.channel_count,
            "last_activity": self.last_activity,
            "full_text": self.full_text,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.metadata
        }
    
    def update_activity_stats(self, message_count: int = None, channel_count: int = None, last_activity: str = None) -> bool:
        """Update activity statistics for this person."""
        updates = {}
        if message_count is not None:
            updates["message_count"] = message_count
            self.message_count = message_count
        if channel_count is not None:
            updates["channel_count"] = channel_count
            self.channel_count = channel_count
        if last_activity is not None:
            updates["last_activity"] = last_activity
            self.last_activity = last_activity
        
        if updates:
            try:
                self.update_document(self.index, self.id, updates)
                return True
            except Exception as e:
                logger.error(f"Error updating activity stats: {e}")
                return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SearchPerson to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            "name": self.name,
            "email": self.email,
            "display_name": self.display_name,
            "title": self.title,
            "department": self.department,
            "bio": self.bio,
            "skills": self.skills,
            "location": self.location,
            "message_count": self.message_count,
            "channel_count": self.channel_count,
            "last_activity": self.last_activity
        })
        return base_dict 