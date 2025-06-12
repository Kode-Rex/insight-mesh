"""
Annotation Migration Detector

This module detects changes to model annotations and generates appropriate
migrations across all data stores (PostgreSQL, Neo4j, Elasticsearch).
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
import json
import hashlib


@dataclass
class AnnotationState:
    """Represents the current state of annotations for a model."""
    model_name: str
    module_path: str
    neo4j_config: Optional[Dict[str, Any]] = None
    elasticsearch_config: Optional[Dict[str, Any]] = None
    neo4j_relationships: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.neo4j_relationships is None:
            self.neo4j_relationships = []


@dataclass
class MigrationChange:
    """Represents a detected change that needs migration."""
    change_type: str  # 'create', 'update', 'delete'
    store_type: str   # 'neo4j', 'elasticsearch'
    model_name: str
    details: Dict[str, Any]


class AnnotationMigrationDetector:
    """Detects changes to model annotations and generates migrations."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_file = project_root / '.weave' / 'annotation_state.json'
        self.previous_state = self._load_previous_state()
    
    def _load_previous_state(self) -> Dict[str, AnnotationState]:
        """Load the previous annotation state from disk."""
        if not self.state_file.exists():
            return {}
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            states = {}
            for model_name, state_data in data.items():
                states[model_name] = AnnotationState(**state_data)
            
            return states
        except Exception:
            return {}
    
    def _save_current_state(self, current_state: Dict[str, AnnotationState]):
        """Save the current annotation state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        data = {}
        for model_name, state in current_state.items():
            data[model_name] = {
                'model_name': state.model_name,
                'module_path': state.module_path,
                'neo4j_config': state.neo4j_config,
                'elasticsearch_config': state.elasticsearch_config,
                'neo4j_relationships': state.neo4j_relationships
            }
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _scan_for_annotated_models(self) -> Dict[str, AnnotationState]:
        """Scan the project for models with annotations."""
        annotated_models = {}
        
        # Scan domain data modules
        domain_path = self.project_root / 'domain' / 'data'
        if domain_path.exists():
            for module_dir in domain_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith('_'):
                    self._scan_module_directory(module_dir, annotated_models)
        
        return annotated_models
    
    def _scan_module_directory(self, module_dir: Path, annotated_models: Dict[str, AnnotationState]):
        """Scan a module directory for annotated models."""
        for py_file in module_dir.glob('*.py'):
            if py_file.name.startswith('_'):
                continue
            
            # Convert file path to module path
            relative_path = py_file.relative_to(self.project_root)
            module_path = '.'.join(relative_path.with_suffix('').parts)
            
            try:
                # Import the module
                module = importlib.import_module(module_path)
                
                # Scan for annotated classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if self._is_annotated_model(obj):
                        state = self._extract_annotation_state(obj, module_path)
                        annotated_models[f"{module_path}:{name}"] = state
                        
            except Exception as e:
                # Skip modules that can't be imported
                continue
    
    def _is_annotated_model(self, cls) -> bool:
        """Check if a class has annotation configurations."""
        return (hasattr(cls, '_neo4j_node_config') or 
                hasattr(cls, '_elasticsearch_config') or
                hasattr(cls, '_neo4j_relationships'))
    
    def _extract_annotation_state(self, cls, module_path: str) -> AnnotationState:
        """Extract the current annotation state from a model class."""
        neo4j_config = None
        if hasattr(cls, '_neo4j_node_config'):
            config = cls._neo4j_node_config
            neo4j_config = {
                'label': config.label,
                'properties': config.properties,
                'id_field': config.id_field,
                'exclude_fields': config.exclude_fields
            }
        
        elasticsearch_config = None
        if hasattr(cls, '_elasticsearch_config'):
            config = cls._elasticsearch_config
            elasticsearch_config = {
                'index_name': config.index_name,
                'doc_type': config.doc_type,
                'properties': config.properties,
                'id_field': config.id_field,
                'exclude_fields': config.exclude_fields,
                'text_fields': config.text_fields,
                'mapping': config.mapping
            }
        
        neo4j_relationships = []
        if hasattr(cls, '_neo4j_relationships'):
            for rel in cls._neo4j_relationships:
                target_model = rel.target_model
                if not isinstance(target_model, str):
                    target_model = f"{target_model.__module__}:{target_model.__name__}"
                
                neo4j_relationships.append({
                    'type': rel.type,
                    'target_model': target_model,
                    'source_field': rel.source_field,
                    'target_field': rel.target_field,
                    'properties': rel.properties
                })
        
        return AnnotationState(
            model_name=cls.__name__,
            module_path=module_path,
            neo4j_config=neo4j_config,
            elasticsearch_config=elasticsearch_config,
            neo4j_relationships=neo4j_relationships
        )
    
    def detect_changes(self) -> List[MigrationChange]:
        """Detect changes between previous and current annotation state."""
        current_state = self._scan_for_annotated_models()
        changes = []
        
        # Check for new or updated models
        for model_key, current in current_state.items():
            previous = self.previous_state.get(model_key)
            
            if previous is None:
                # New annotated model
                changes.extend(self._generate_create_changes(current))
            else:
                # Check for updates
                changes.extend(self._generate_update_changes(previous, current))
        
        # Check for deleted models
        for model_key, previous in self.previous_state.items():
            if model_key not in current_state:
                changes.extend(self._generate_delete_changes(previous))
        
        # Save current state
        self._save_current_state(current_state)
        
        return changes
    
    def _generate_create_changes(self, state: AnnotationState) -> List[MigrationChange]:
        """Generate changes for a newly annotated model."""
        changes = []
        
        if state.neo4j_config:
            changes.append(MigrationChange(
                change_type='create',
                store_type='neo4j',
                model_name=state.model_name,
                details={
                    'action': 'create_node_label',
                    'label': state.neo4j_config['label'],
                    'properties': state.neo4j_config,
                    'relationships': state.neo4j_relationships
                }
            ))
        
        if state.elasticsearch_config:
            changes.append(MigrationChange(
                change_type='create',
                store_type='elasticsearch',
                model_name=state.model_name,
                details={
                    'action': 'create_index',
                    'index_name': state.elasticsearch_config['index_name'],
                    'config': state.elasticsearch_config
                }
            ))
        
        return changes
    
    def _generate_update_changes(self, previous: AnnotationState, current: AnnotationState) -> List[MigrationChange]:
        """Generate changes for an updated model."""
        changes = []
        
        # Check Neo4j changes
        if self._configs_different(previous.neo4j_config, current.neo4j_config):
            if current.neo4j_config is None:
                # Neo4j annotation removed
                changes.append(MigrationChange(
                    change_type='delete',
                    store_type='neo4j',
                    model_name=current.model_name,
                    details={'action': 'remove_node_label', 'label': previous.neo4j_config['label']}
                ))
            elif previous.neo4j_config is None:
                # Neo4j annotation added
                changes.extend(self._generate_create_changes(current))
            else:
                # Neo4j annotation updated
                changes.append(MigrationChange(
                    change_type='update',
                    store_type='neo4j',
                    model_name=current.model_name,
                    details={
                        'action': 'update_node_label',
                        'old_config': previous.neo4j_config,
                        'new_config': current.neo4j_config
                    }
                ))
        
        # Check Elasticsearch changes
        if self._configs_different(previous.elasticsearch_config, current.elasticsearch_config):
            if current.elasticsearch_config is None:
                # Elasticsearch annotation removed
                changes.append(MigrationChange(
                    change_type='delete',
                    store_type='elasticsearch',
                    model_name=current.model_name,
                    details={'action': 'remove_index', 'index_name': previous.elasticsearch_config['index_name']}
                ))
            elif previous.elasticsearch_config is None:
                # Elasticsearch annotation added
                changes.extend(self._generate_create_changes(current))
            else:
                # Elasticsearch annotation updated
                changes.append(MigrationChange(
                    change_type='update',
                    store_type='elasticsearch',
                    model_name=current.model_name,
                    details={
                        'action': 'update_index',
                        'old_config': previous.elasticsearch_config,
                        'new_config': current.elasticsearch_config
                    }
                ))
        
        # Check relationship changes
        if previous.neo4j_relationships != current.neo4j_relationships:
            changes.append(MigrationChange(
                change_type='update',
                store_type='neo4j',
                model_name=current.model_name,
                details={
                    'action': 'update_relationships',
                    'old_relationships': previous.neo4j_relationships,
                    'new_relationships': current.neo4j_relationships
                }
            ))
        
        return changes
    
    def _generate_delete_changes(self, state: AnnotationState) -> List[MigrationChange]:
        """Generate changes for a deleted model."""
        changes = []
        
        if state.neo4j_config:
            changes.append(MigrationChange(
                change_type='delete',
                store_type='neo4j',
                model_name=state.model_name,
                details={'action': 'remove_node_label', 'label': state.neo4j_config['label']}
            ))
        
        if state.elasticsearch_config:
            changes.append(MigrationChange(
                change_type='delete',
                store_type='elasticsearch',
                model_name=state.model_name,
                details={'action': 'remove_index', 'index_name': state.elasticsearch_config['index_name']}
            ))
        
        return changes
    
    def _configs_different(self, config1: Optional[Dict], config2: Optional[Dict]) -> bool:
        """Check if two configurations are different."""
        if config1 is None and config2 is None:
            return False
        if config1 is None or config2 is None:
            return True
        
        # Compare JSON representations for deep equality
        return json.dumps(config1, sort_keys=True) != json.dumps(config2, sort_keys=True)


def generate_migration_files(changes: List[MigrationChange], project_root: Path, message: str) -> Dict[str, str]:
    """Generate migration files for the detected changes."""
    migration_files = {}
    
    # Group changes by store type
    neo4j_changes = [c for c in changes if c.store_type == 'neo4j']
    elasticsearch_changes = [c for c in changes if c.store_type == 'elasticsearch']
    
    # Generate Neo4j migration
    if neo4j_changes:
        neo4j_migration = _generate_neo4j_migration(neo4j_changes, message)
        migration_files['neo4j'] = neo4j_migration
    
    # Generate Elasticsearch migration
    if elasticsearch_changes:
        es_migration = _generate_elasticsearch_migration(elasticsearch_changes, message)
        migration_files['elasticsearch'] = es_migration
    
    return migration_files


def _generate_neo4j_migration(changes: List[MigrationChange], message: str) -> str:
    """Generate a Neo4j migration file content."""
    operations = []
    
    for change in changes:
        if change.details['action'] == 'create_node_label':
            operations.append(f"""
    # Create constraints for {change.model_name}
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:{change.details['label']}) REQUIRE n.{change.details['properties']['id_field']} IS UNIQUE")
    
    # Create indexes for searchable properties
    # Add any additional indexes as needed
""")
        elif change.details['action'] == 'update_node_label':
            operations.append(f"""
    # Update {change.model_name} node configuration
    # Note: Manual review may be needed for property changes
""")
        elif change.details['action'] == 'remove_node_label':
            operations.append(f"""
    # Remove {change.model_name} nodes and constraints
    session.run("DROP CONSTRAINT IF EXISTS FOR (n:{change.details['label']}) REQUIRE n.id IS UNIQUE")
    session.run("MATCH (n:{change.details['label']}) DELETE n")
""")
    
    return f'''"""
{message}

Revision ID: neo4j_{{revision_id}}
Revises: {{down_revision}}
Create Date: {{create_date}}
"""

def upgrade():
    """Apply Neo4j schema changes."""
    from neo4j import GraphDatabase
    import os
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
    )
    
    with driver.session() as session:
{''.join(operations)}
    
    driver.close()


def downgrade():
    """Reverse Neo4j schema changes."""
    # Implement downgrade logic as needed
    pass
'''


def _generate_elasticsearch_migration(changes: List[MigrationChange], message: str) -> str:
    """Generate an Elasticsearch migration file content."""
    operations = []
    
    for change in changes:
        if change.details['action'] == 'create_index':
            config = change.details['config']
            operations.append(f"""
    # Create index for {change.model_name}
    index_name = "{config['index_name']}"
    
    if not es.indices.exists(index=index_name):
        mapping = {{
            "mappings": {{
                "properties": {{
                    # Auto-generated mapping - review and customize as needed
                }}
            }}
        }}
        es.indices.create(index=index_name, body=mapping)
        print(f"Created index: {{index_name}}")
""")
        elif change.details['action'] == 'update_index':
            operations.append(f"""
    # Update index for {change.model_name}
    # Note: Index updates may require reindexing data
""")
        elif change.details['action'] == 'remove_index':
            operations.append(f"""
    # Remove index for {change.model_name}
    index_name = "{change.details['index_name']}"
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"Deleted index: {{index_name}}")
""")
    
    return f'''"""
{message}

Revision ID: es_{{revision_id}}
Revises: {{down_revision}}
Create Date: {{create_date}}
"""

def upgrade():
    """Apply Elasticsearch schema changes."""
    from elasticsearch import Elasticsearch
    import os
    
    es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
    es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
    es_scheme = os.getenv("ELASTICSEARCH_SCHEME", "http")
    
    es = Elasticsearch([f"{{es_scheme}}://{{es_host}}:{{es_port}}"])
    
{''.join(operations)}


def downgrade():
    """Reverse Elasticsearch schema changes."""
    # Implement downgrade logic as needed
    pass
''' 