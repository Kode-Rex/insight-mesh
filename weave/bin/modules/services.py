import subprocess
import json
import webbrowser
from rich.console import Console
from rich.table import Table

from .config import (
    get_config, 
    get_service_for_container, 
    get_service_by_id
)
from .docker_commands import extract_urls

console = Console()

def list_services(project_name, verbose=False, debug=False):
    """List all running Docker services with URLs"""
    prefix = project_name
    
    if debug:
        console.print("[bold]Config:[/bold]")
        console.print(get_config())
    
    # Get running containers with the project prefix
    command = f"docker ps --format '{{{{.ID}}}}|{{{{.Names}}}}|{{{{.Ports}}}}|{{{{.Image}}}}' | grep {prefix}"
    
    if verbose or debug:
        console.print(f"[bold blue]Running:[/bold blue] {command}")
    
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0 and result.returncode != 1:  # grep returns 1 if no matches
        console.print(f"[bold red]Error:[/bold red] {result.stderr}")
        return
    
    if not result.stdout.strip():
        console.print("[yellow]No services found.[/yellow]")
        return
    
    # Group containers by service
    services = {}
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) >= 4:
            container_id, container_name, ports, image = parts[0], parts[1], parts[2], parts[3]
            
            if debug:
                console.print(f"[cyan]Processing container:[/cyan] {container_name} / {image}")
            
            # Get service info
            service_id, service_info = get_service_for_container(container_name, image)
            
            if debug:
                if service_id:
                    console.print(f"[green]  Matched service:[/green] {service_id}")
                else:
                    console.print(f"[yellow]  No match found[/yellow]")
            
            # If no service found, create a generic one
            if not service_id:
                service_id = f"unknown-{container_name}"
                service_info = {
                    "display_name": container_name,
                    "description": "Unknown service"
                }
            
            # Extract URLs
            urls = extract_urls(ports)
            
            # Add to services dict
            if service_id not in services:
                services[service_id] = {
                    "display_name": service_info.get("display_name", service_id),
                    "description": service_info.get("description", ""),
                    "containers": [],
                    "urls": set()
                }
            
            services[service_id]["containers"].append({
                "id": container_id,
                "name": container_name,
                "image": image,
                "ports": ports,
                "urls": urls
            })
            
            # Add URLs to set
            for url in urls:
                services[service_id]["urls"].add(url)
    
    # Display results
    table = Table("Service", "Display Name", "Description", "Containers", "URLs")
    
    for service_id, info in sorted(services.items()):
        container_names = [c["name"] for c in info["containers"]]
        urls = list(info["urls"])
        
        table.add_row(
            service_id,
            info["display_name"],
            info["description"] or "-",
            "\n".join(container_names),
            "\n".join(urls) if urls else "N/A"
        )
    
    console.print(table)

    # If verbose, also show detailed container information
    if verbose:
        console.print("\n[bold]Detailed Container Information:[/bold]")
        
        for service_id, info in services.items():
            console.print(f"\n[bold cyan]{info['display_name']} ({service_id})[/bold cyan]")
            
            container_table = Table("Container ID", "Container Name", "Image", "Ports", "URLs")
            
            for container in info["containers"]:
                container_table.add_row(
                    container["id"],
                    container["name"],
                    container["image"],
                    container["ports"],
                    "\n".join(container["urls"]) if container["urls"] else "N/A"
                )
            
            console.print(container_table)

def open_service(project_name, service_identifier, verbose=False):
    """Open a service in the browser"""
    prefix = project_name
    
    # Get running containers with the project prefix
    command = f"docker ps --format '{{{{.ID}}}}|{{{{.Names}}}}|{{{{.Ports}}}}|{{{{.Image}}}}' | grep {prefix}"
    
    if verbose:
        console.print(f"[bold blue]Running:[/bold blue] {command}")
    
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0 and result.returncode != 1:  # grep returns 1 if no matches
        console.print(f"[bold red]Error:[/bold red] {result.stderr}")
        return
    
    # Parse containers and group by service
    running_containers = []
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        parts = line.split('|')
        if len(parts) >= 4:
            container_id, container_name, ports, image = parts[0], parts[1], parts[2], parts[3]
            
            # Get service info
            service_id, service_info = get_service_for_container(container_name, image)
            
            running_containers.append({
                'container_id': container_id,
                'name': container_name,
                'ports': ports,
                'image': image,
                'service_id': service_id,
                'service_info': service_info
            })
    
    if not running_containers:
        console.print("[yellow]No services found.[/yellow]")
        return
    
    # Try to find the service/container by various identifiers
    target_containers = []
    
    # 1. Check if it's a direct service ID
    service_info = get_service_by_id(service_identifier)
    if service_info:
        # Find all containers for this service
        for container in running_containers:
            if container['service_id'] == service_identifier:
                target_containers.append(container)
    
    # 2. Check for display name match
    if not target_containers:
        config = get_config()
        services = config.get("services", {})
        for service_id, info in services.items():
            if service_identifier == info.get("display_name"):
                # Find all containers for this service
                for container in running_containers:
                    if container['service_id'] == service_id:
                        target_containers.append(container)
                break
    
    # 3. Check for container name match (direct or partial)
    if not target_containers:
        for container in running_containers:
            if service_identifier == container['name'] or service_identifier in container['name']:
                target_containers.append(container)
                break
    
    if not target_containers:
        console.print(f"[yellow]Service '{service_identifier}' not found[/yellow]")
        return
    
    # Find the first container with URLs
    container_with_urls = None
    for container in target_containers:
        urls = extract_urls(container['ports'])
        if urls:
            container_with_urls = container
            container_with_urls['urls'] = urls
            break
    
    if not container_with_urls:
        console.print(f"[yellow]No URLs available for service '{service_identifier}'[/yellow]")
        return
    
    # Get service info for display
    display_name = container_with_urls['service_info'].get('display_name', 
                                                         container_with_urls['service_id'] or 
                                                         container_with_urls['name'])
    
    # Open the first URL in a browser
    url = container_with_urls['urls'][0]
    
    # Ensure the URL uses localhost instead of 0.0.0.0
    if '0.0.0.0' in url:
        url = url.replace('0.0.0.0', 'localhost')
    
    webbrowser.open(url)
    console.print(f"Opened {display_name} in default browser: {url}")

def get_rag_logs(project_name, follow=False, tail=100, verbose=False, filter_logs=True):
    """Get logs from the RAG handler in the LiteLLM container"""
    litellm_container = f"{project_name}-litellm-1"
    
    # First check if the LiteLLM container is running
    check_cmd = ['docker', 'ps', '--filter', f"name={litellm_container}", '--format', '{{.Names}}']
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    
    if not result.stdout.strip():
        console.print(f"[bold red]Error:[/bold red] LiteLLM container '{litellm_container}' is not running")
        return
    
    # Base command to get RAG logs
    rag_cmd = ['docker', 'exec', litellm_container, 'cat', '/app/rag_handler.log']
    
    if follow:
        # For follow mode, we'll use 'tail -f' inside the container
        rag_cmd = ['docker', 'exec', litellm_container, 'tail', '-f', '-n', str(tail), '/app/rag_handler.log']
    
    if verbose:
        console.print(f"[bold blue]Running:[/bold blue] {' '.join(rag_cmd)}")
    
    # If follow mode is on, we'll just run the command directly
    if follow:
        if not filter_logs:
            # Show all logs
            subprocess.run(rag_cmd)
        else:
            # Create a grep filter command to exclude noise
            filter_cmd = ['grep', '-v', '-E', 
                          'Spend transactions|Daily|encrypt_decrypt_utils|proxy_server\\.py|len new_models|hanging_request']
            
            # Pipe the output through grep
            p1 = subprocess.Popen(rag_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(filter_cmd, stdin=p1.stdout)
            
            # Wait for the commands to complete
            p2.communicate()
        return
    
    # Run the command and capture output for non-follow mode
    result = subprocess.run(rag_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        console.print(f"[bold red]Error:[/bold red] {result.stderr}")
        return
    
    # Display logs based on verbosity
    if not filter_logs:
        # Show all logs
        console.print(result.stdout)
    else:
        # Filter out noise from the logs for better readability
        filtered_logs = []
        for line in result.stdout.split('\n'):
            # Skip lines with these patterns
            if any(pattern in line for pattern in [
                "Spend transactions", 
                "Daily", 
                "encrypt_decrypt_utils", 
                "proxy_server.py", 
                "len new_models", 
                "hanging_request"
            ]):
                continue
            filtered_logs.append(line)
        
        # Display the filtered logs
        console.print("\n".join(filtered_logs)) 