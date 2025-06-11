#!/usr/bin/env python

import json
import subprocess
import os
from pathlib import Path
from rich.console import Console
from typing import Dict, List, Optional

console = Console()

def get_project_root() -> Path:
    """Get the project root directory"""
    return Path.cwd()

def get_config_path() -> Path:
    """Get the path to the config.json file"""
    return get_project_root() / '.weave' / 'config.json'

def load_config() -> Dict:
    """Load the configuration from config.json"""
    config_path = get_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def get_databases_config() -> Dict:
    """Get the databases configuration"""
    config = load_config()
    return config.get('databases', {})

def get_managed_databases() -> List[str]:
    """Get list of databases managed by weave"""
    databases_config = get_databases_config()
    return [
        db_name for db_name, db_config in databases_config.items()
        if db_config.get('managed_by') == 'weave'
    ]

def get_all_databases() -> List[str]:
    """Get list of all databases"""
    databases_config = get_databases_config()
    return list(databases_config.keys())

def get_database_choices() -> List[str]:
    """Get database choices for CLI commands (managed databases + 'all')"""
    managed = get_managed_databases()
    return managed + ['all']

def get_database_description(db_name: str) -> Optional[str]:
    """Get description for a database"""
    databases_config = get_databases_config()
    return databases_config.get(db_name, {}).get('description')

def get_config():
    """
    Read configuration from config.json file.
    Try multiple locations in the following order:
    1. User's home directory (~/.weave/config.json)
    2. Current directory (.weave/config.json)
    3. Parent directory (../.weave/config.json)
    4. Any parent directory up the tree
    """
    try:
        # First try home directory
        config_path = Path.home() / '.weave' / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Then try current directory
        config_path = Path('.weave') / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Then try parent directory (project root)
        config_path = Path('..') / '.weave' / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Search up the directory tree
        current_path = Path.cwd()
        while current_path != current_path.parent:
            config_path = current_path / '.weave' / 'config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            current_path = current_path.parent
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read config file: {str(e)}[/yellow]")
    
    return {"project_name": "insight-mesh", "services": {}}  # Default value

def get_project_name():
    """Get the project name from config"""
    return get_config().get("project_name", "insight-mesh")

def get_service_info(container_name):
    """Get service info for a container name"""
    config = get_config()
    mappings = config.get("container_mappings", {})
    
    # First try exact match
    if container_name in mappings:
        return mappings[container_name]
    
    # Then try partial match (for when container names have dynamic suffixes)
    for pattern, info in mappings.items():
        if pattern in container_name:
            return info
    
    return {}

def get_service_info_by_container(container_name):
    """Get service info for a container name"""
    config = get_config()
    mappings = config.get("container_mappings", {})
    
    # First try exact match
    if container_name in mappings:
        return mappings[container_name]
    
    # Then try partial match (for when container names have dynamic suffixes)
    for pattern, info in mappings.items():
        if pattern in container_name:
            return info
    
    return {}

def get_service_info_by_image(image_name):
    """Get service info for an image name"""
    config = get_config()
    image_mappings = config.get("images", {})
    
    # First try exact match
    if image_name in image_mappings:
        service_name = image_mappings[image_name]
        # Find the service info by service name
        for _, info in config.get("container_mappings", {}).items():
            if info.get("service") == service_name:
                return info
    
    # Then try partial match
    for pattern, service_name in image_mappings.items():
        if pattern in image_name:
            # Find the service info by service name
            for _, info in config.get("container_mappings", {}).items():
                if info.get("service") == service_name:
                    return info
    
    return {}

def get_service_for_container(container_name, image_name):
    """Find the service that matches a container name or image name"""
    config = get_config()
    services = config.get("services", {})
    
    # Sort services to prioritize more specific patterns (longer patterns first)
    # This ensures database services with specific patterns like "postgres_openwebui-" 
    # match before general services with patterns like "openwebui"
    sorted_services = sorted(services.items(), key=lambda x: max(len(p) for p in x[1].get("container_patterns", [""])), reverse=True)
    
    # For each service, check if the container name or image matches any patterns
    for service_id, service_info in sorted_services:
        # Check container name patterns first (more specific)
        container_patterns = service_info.get("container_patterns", [])
        for pattern in container_patterns:
            if pattern in container_name:
                return service_id, service_info
    
    # Only check image patterns if no container pattern matched
    # This prevents all postgres containers from matching the first postgres service
    for service_id, service_info in sorted_services:
        # Check image patterns
        image_patterns = service_info.get("images", [])
        for pattern in image_patterns:
            if pattern in image_name:
                return service_id, service_info
    
    return None, {}

def get_service_by_id(service_id):
    """Get service info by its ID"""
    config = get_config()
    services = config.get("services", {})
    return services.get(service_id, {})

def get_docker_service_name(service_identifier, project_name):
    """
    Convert a service identifier (from config.json) to a Docker service name
    
    Args:
        service_identifier: The service ID, display name, or docker service name
        project_name: The project name prefix for Docker containers
        
    Returns:
        The matching Docker service name or the original identifier if no match found
    """
    # Get list of docker-compose services
    cmd = ['docker', 'compose', 'config', '--services']
    result = subprocess.run(cmd, capture_output=True, text=True)
    docker_services = result.stdout.strip().split('\n') if result.returncode == 0 else []
    
    # If the identifier is already a Docker service, return it
    if service_identifier in docker_services:
        return service_identifier
    
    config = get_config()
    services = config.get("services", {})
    
    # Check if it's a service ID in our config
    if service_identifier in services:
        service_info = services[service_identifier]
        container_patterns = service_info.get("container_patterns", [])
        
        # Try to match container patterns to docker-compose services
        # First try exact matches, then partial matches
        for pattern in container_patterns:
            # Try exact match first
            if pattern in docker_services:
                return pattern
            # Then try partial matches
            for docker_svc in docker_services:
                if pattern in docker_svc:
                    return docker_svc
    
    # Check if it's a display name in our config
    for service_id, info in services.items():
        if service_identifier == info.get("display_name"):
            container_patterns = info.get("container_patterns", [])
            
            # Try to match container patterns to docker-compose services
            # First try exact matches, then partial matches
            for pattern in container_patterns:
                # Try exact match first
                if pattern in docker_services:
                    return pattern
                # Then try partial matches
                for docker_svc in docker_services:
                    if pattern in docker_svc:
                        return docker_svc
    
    # If no match found, return the original identifier
    return service_identifier

def get_service_id_for_docker_service(docker_service_name):
    """
    Convert a Docker service name to a service ID from config.json
    
    Args:
        docker_service_name: The Docker service name
        
    Returns:
        The matching service ID from config.json or the original Docker service name if no match found
    """
    config = get_config()
    services = config.get("services", {})
    
    # Try to find a service with a matching container pattern
    for service_id, service_info in services.items():
        container_patterns = service_info.get("container_patterns", [])
        for pattern in container_patterns:
            if pattern in docker_service_name:
                return service_id
    
    # If no match found, return the original Docker service name
    return docker_service_name

def get_databases_by_type(db_type: str) -> List[str]:
    """Get list of databases by type (sql, graph, search)"""
    databases_config = get_databases_config()
    return [
        db_name for db_name, db_config in databases_config.items()
        if db_config.get('type') == db_type and db_config.get('managed_by') == 'weave'
    ]

def get_database_type(db_name: str) -> Optional[str]:
    """Get the type of a database (sql, graph, search)"""
    databases_config = get_databases_config()
    return databases_config.get(db_name, {}).get('type')

def get_database_migration_tool(db_name: str) -> Optional[str]:
    """Get the migration tool for a database based on its type"""
    db_type = get_database_type(db_name)
    if not db_type:
        return None
    
    # Get migration tool from frameworks configuration
    config = load_config()
    frameworks = config.get('frameworks', {})
    framework_config = frameworks.get(db_type, {})
    return framework_config.get('migration_tool')

def get_database_connection_config(db_name: str) -> Dict:
    """Get connection configuration for a database"""
    databases_config = get_databases_config()
    return databases_config.get(db_name, {}).get('connection', {})

def get_sql_databases() -> List[str]:
    """Get list of SQL databases (PostgreSQL with Alembic)"""
    return get_databases_by_type('sql')

def get_graph_databases() -> List[str]:
    """Get list of graph databases (Neo4j)"""
    return get_databases_by_type('graph')

def get_search_databases() -> List[str]:
    """Get list of search databases (Elasticsearch)"""
    return get_databases_by_type('search')

def get_all_database_types() -> List[str]:
    """Get all unique database types"""
    databases_config = get_databases_config()
    types = set()
    for db_config in databases_config.values():
        if db_config.get('managed_by') == 'weave':
            db_type = db_config.get('type')
            if db_type:
                types.add(db_type)
    return sorted(list(types))

def is_database_managed(db_name: str) -> bool:
    """Check if a database is managed by weave"""
    databases_config = get_databases_config()
    db_config = databases_config.get(db_name, {})
    return db_config.get('managed_by') == 'weave' 