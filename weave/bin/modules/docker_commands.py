import subprocess
import time
from rich.console import Console

console = Console()

def run_command(command, verbose=False):
    """Run a shell command and return the result"""
    try:
        if verbose:
            console.print(f"[bold blue]Running:[/bold blue] {' '.join(command)}")
            
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error:[/bold red] {result.stderr}")
            return False
            
        if verbose and result.stdout:
            console.print(result.stdout)
            
        return True
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False

def run_service_up_with_feedback(command, project_name, verbose=False):
    """Run docker compose up with real-time feedback as services come online"""
    try:
        console.print("[bold green]Starting services...[/bold green]")
        
        # Run the docker compose up command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error starting services:[/bold red] {result.stderr}")
            return False
        
        # Show any output from the command
        if result.stdout.strip():
            console.print(result.stdout.strip())
        
        # Extract the specific services being started from the command
        # The command format is: ['docker', 'compose', '-p', project_name, 'up', '-d', service1, service2, ...]
        expected_services = set()
        if len(command) > 6:  # If there are services specified after 'up -d'
            expected_services = set(command[6:])  # Get services from command
        else:
            # If no specific services, get all services from docker-compose
            services_cmd = ['docker', 'compose', '-p', project_name, 'ps', '--services']
            services_result = subprocess.run(services_cmd, capture_output=True, text=True)
            
            if services_result.returncode == 0:
                expected_services = set(services_result.stdout.strip().split('\n'))
                if expected_services == {''}:  # Handle empty result
                    expected_services = set()
        
        if not expected_services:
            console.print("[blue]No services to monitor[/blue]")
            return True
        
        # Now monitor services as they come online
        console.print("[blue]Monitoring services as they come online...[/blue]")
        
        # Monitor services coming online
        online_services = set()
        max_attempts = 30  # Wait up to 30 seconds
        attempt = 0
        
        while attempt < max_attempts and len(online_services) < len(expected_services):
            # Check which services are running
            ps_cmd = ['docker', 'compose', '-p', project_name, 'ps', '--format', 'json']
            ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
            
            if ps_result.returncode == 0:
                import json
                try:
                    # Parse each line as JSON (docker compose ps --format json outputs one JSON object per line)
                    current_online = set()
                    for line in ps_result.stdout.strip().split('\n'):
                        if line.strip():
                            container_info = json.loads(line)
                            service_name = container_info.get('Service', '')
                            state = container_info.get('State', '')
                            
                            # Only track services we're actually starting
                            if state == 'running' and service_name in expected_services:
                                current_online.add(service_name)
                                
                                # Show newly online services
                                if service_name not in online_services:
                                    console.print(f"[green]✓[/green] {service_name} is now online")
                    
                    online_services = current_online
                    
                except json.JSONDecodeError:
                    # Fallback to simpler parsing if JSON fails
                    pass
            
            if len(online_services) < len(expected_services):
                time.sleep(1)
                attempt += 1
        
        # Final status
        if len(online_services) == len(expected_services) and len(expected_services) > 0:
            console.print(f"[bold green]All {len(expected_services)} services are now online![/bold green]")
        elif len(expected_services) > 0:
            console.print(f"[yellow]{len(online_services)}/{len(expected_services)} services are online[/yellow]")
            
            # Show which services are still starting
            offline_services = expected_services - online_services
            if offline_services:
                console.print(f"[yellow]Still starting: {', '.join(sorted(offline_services))}[/yellow]")
        
        # Show URLs if available (only for the services we started)
        show_service_urls(project_name, expected_services)
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False

def run_service_restart_with_feedback(command, project_name, verbose=False):
    """Run docker compose restart with real-time feedback as services restart"""
    try:
        console.print("[bold yellow]Restarting services...[/bold yellow]")
        
        # Extract the specific services being restarted from the command
        # The command format is: ['docker', 'compose', '-p', project_name, 'restart', service1, service2, ...]
        expected_services = set()
        if len(command) > 5:  # If there are services specified after 'restart'
            expected_services = set(command[5:])  # Get services from command
        else:
            # If no specific services, get all services from docker-compose
            services_cmd = ['docker', 'compose', '-p', project_name, 'ps', '--services']
            services_result = subprocess.run(services_cmd, capture_output=True, text=True)
            
            if services_result.returncode == 0:
                expected_services = set(services_result.stdout.strip().split('\n'))
                if expected_services == {''}:  # Handle empty result
                    expected_services = set()
        
        if not expected_services:
            console.print("[blue]No services to restart[/blue]")
            return True
        
        # Run the docker compose restart command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error restarting services:[/bold red] {result.stderr}")
            return False
        
        # Show any output from the command
        if result.stdout.strip():
            console.print(result.stdout.strip())
        
        # Now monitor services as they come back online
        console.print("[blue]Monitoring services as they come back online...[/blue]")
        
        # Monitor services coming online
        online_services = set()
        max_attempts = 30  # Wait up to 30 seconds
        attempt = 0
        
        while attempt < max_attempts and len(online_services) < len(expected_services):
            # Check which services are running
            ps_cmd = ['docker', 'compose', '-p', project_name, 'ps', '--format', 'json']
            ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
            
            if ps_result.returncode == 0:
                import json
                try:
                    # Parse each line as JSON (docker compose ps --format json outputs one JSON object per line)
                    current_online = set()
                    for line in ps_result.stdout.strip().split('\n'):
                        if line.strip():
                            container_info = json.loads(line)
                            service_name = container_info.get('Service', '')
                            state = container_info.get('State', '')
                            
                            # Only track services we're actually restarting
                            if state == 'running' and service_name in expected_services:
                                current_online.add(service_name)
                                
                                # Show newly online services
                                if service_name not in online_services:
                                    console.print(f"[green]✓[/green] {service_name} is back online")
                    
                    online_services = current_online
                    
                except json.JSONDecodeError:
                    # Fallback to simpler parsing if JSON fails
                    pass
            
            if len(online_services) < len(expected_services):
                time.sleep(1)
                attempt += 1
        
        # Final status
        if len(online_services) == len(expected_services) and len(expected_services) > 0:
            console.print(f"[bold green]All {len(expected_services)} services have been restarted successfully![/bold green]")
        elif len(expected_services) > 0:
            console.print(f"[yellow]{len(online_services)}/{len(expected_services)} services are online[/yellow]")
            
            # Show which services are still starting
            offline_services = expected_services - online_services
            if offline_services:
                console.print(f"[yellow]Still restarting: {', '.join(sorted(offline_services))}[/yellow]")
        
        # Show URLs if available (only for the services we restarted)
        show_service_urls(project_name, expected_services)
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False

def show_service_urls(project_name, services):
    """Show URLs for running services"""
    try:
        # Get running containers with ports
        ps_cmd = ['docker', 'ps', '--format', '{{.Names}}|{{.Ports}}', '--filter', f'label=com.docker.compose.project={project_name}']
        result = subprocess.run(ps_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            urls_found = False
            console.print("\n[bold blue]Service URLs:[/bold blue]")
            
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    name, ports = line.split('|', 1)
                    urls = extract_urls(ports)
                    if urls:
                        service_name = name.replace(f'{project_name}-', '').replace('-1', '')
                        # Only show URLs for the services we started
                        if service_name in services:
                            urls_found = True
                            console.print(f"  {service_name}: {', '.join(urls)}")
            
            if not urls_found:
                console.print("  [dim]No exposed ports found for started services[/dim]")
    except Exception:
        pass  # Silently fail for URL display
        
def extract_urls(ports_string):
    """Extract URLs from Docker port mappings"""
    urls = []
    if not ports_string:
        return urls
    
    for port_mapping in ports_string.split(','):
        if '->' in port_mapping and 'tcp' in port_mapping:
            try:
                host_part = port_mapping.split('->')[0].strip()
                if ':' in host_part:
                    host, port = host_part.split(':')
                    # Replace 0.0.0.0 with localhost
                    if host == '0.0.0.0':
                        host = 'localhost'
                    urls.append(f"http://{host}:{port}")
                else:
                    port = host_part
                    urls.append(f"http://localhost:{port}")
            except Exception:
                pass
    return urls 