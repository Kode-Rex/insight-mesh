import json
import subprocess
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
    
    return {"project_id": "insight-mesh", "services": {}}  # Default value

def get_project_name():
    """Get the project name from config"""
    return get_config().get("project_id", "insight-mesh")

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
    cmd = ['docker', 'compose', '-p', project_name, 'ps', '--services']
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
        for docker_svc in docker_services:
            for pattern in container_patterns:
                if pattern in docker_svc:
                    return docker_svc
    
    # Check if it's a display name in our config
    for service_id, info in services.items():
        if service_identifier == info.get("display_name"):
            container_patterns = info.get("container_patterns", [])
            
            # Try to match container patterns to docker-compose services
            for docker_svc in docker_services:
                for pattern in container_patterns:
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