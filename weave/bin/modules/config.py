import json
from pathlib import Path
from rich.console import Console

console = Console()

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
    
    # Special case for postgres containers - match them exactly
    if "postgres" in container_name:
        for service_id, service_info in services.items():
            if service_id.startswith("postgres-"):
                container_patterns = service_info.get("container_patterns", [])
                for pattern in container_patterns:
                    if pattern in container_name:
                        return service_id, service_info
    
    # For each service, check if the container name or image matches any patterns
    for service_id, service_info in services.items():
        # Skip postgres services for non-postgres containers
        if service_id.startswith("postgres-") and "postgres" not in container_name:
            continue
            
        # Check container name patterns
        container_patterns = service_info.get("container_patterns", [])
        for pattern in container_patterns:
            if pattern in container_name:
                return service_id, service_info
        
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