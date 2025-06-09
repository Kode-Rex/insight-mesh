#!/usr/bin/env python

import os
import sys
import subprocess
import click
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from dotenv import load_dotenv
from pathlib import Path

from .config import get_project_name, get_docker_service_name, get_service_id_for_docker_service
from .docker_commands import run_command
from .services import list_services, open_service, get_rag_logs
from .tools import list_tools, add_tool, remove_tool, install_tool, set_mcp_config_path, get_mcp_config_path, check_tool_availability, get_weave_config

# Load environment variables
load_dotenv()

console = Console()

# Project name to scope all operations
PROJECT_NAME = get_project_name()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Weaver: A Rails-like framework for rapidly building and deploying enterprise-grade GenAI applications."""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose

@cli.command('up')
@click.option('--detach', '-d', is_flag=True, help='Run in detached mode')
@click.option('--service', '-s', multiple=True, help='Specific service(s) to start')
@click.pass_context
def up(ctx, detach, service):
    """Start services using docker-compose up"""
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'up']
    
    if detach:
        command.append('-d')
        
    if service:
        # Convert service IDs from config to docker service names
        docker_services = [get_docker_service_name(s, PROJECT_NAME) for s in service]
        command.extend(docker_services)
        
    verbose = ctx.obj.get('VERBOSE', False)
    
    with console.status("[bold green]Starting services...", spinner="dots"):
        if run_command(command, verbose):
            if detach:
                console.print("[bold green]Services started successfully in detached mode[/bold green]")
            else:
                console.print("[bold green]Services started successfully (press Ctrl+C to stop)[/bold green]")

@cli.command('down')
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes')
@click.option('--remove-orphans', is_flag=True, help='Remove containers for services not in the compose file')
@click.pass_context
def down(ctx, volumes, remove_orphans):
    """Stop services using docker-compose down"""
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'down']
    
    if volumes:
        command.append('-v')
        
    if remove_orphans:
        command.append('--remove-orphans')
        
    verbose = ctx.obj.get('VERBOSE', False)
    
    with console.status("[bold yellow]Stopping services...", spinner="dots"):
        if run_command(command, verbose):
            console.print("[bold green]Services stopped successfully[/bold green]")

@cli.command('logs')
@click.option('--follow', '-f', is_flag=True, help='Follow logs')
@click.option('--tail', '-n', default=100, help='Number of lines to show')
@click.argument('service', required=False)
@click.option('--verbose', '-v', is_flag=True, help='Show detailed logs without filtering')
@click.pass_context
def logs(ctx, follow, tail, service, verbose):
    """Show logs for services
    
    SERVICE can be a Docker service name or a special value:
    
    * rag - Show RAG logs from the LiteLLM container (not a service but a special parameter)
      Example: weave logs rag
    
    The 'rag' parameter extracts and filters logs from the RAG handler in the LiteLLM container.
    Use --verbose to see unfiltered RAG logs.
    """
    is_verbose = ctx.obj.get('VERBOSE', False)
    
    # Special case for RAG logs - when service is "rag"
    if service == "rag":
        get_rag_logs(PROJECT_NAME, follow, tail, is_verbose, not verbose)
        return
    
    # Convert service ID from config to docker service name if needed
    docker_service = get_docker_service_name(service, PROJECT_NAME) if service else None
    
    # Standard Docker Compose logs command
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'logs']
    
    if follow:
        command.append('-f')
        
    command.extend(['--tail', str(tail)])
    
    if docker_service:
        command.append(docker_service)
    
    if is_verbose:
        console.print(f"[bold blue]Running:[/bold blue] {' '.join(command)}")
        
    subprocess.run(command)

@cli.command('restart')
@click.argument('service', required=False)
@click.pass_context
def restart(ctx, service):
    """Restart services"""
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'restart']
    
    # Convert service ID from config to docker service name if needed
    if service:
        docker_service = get_docker_service_name(service, PROJECT_NAME)
        command.append(docker_service)
        
    verbose = ctx.obj.get('VERBOSE', False)
    
    with console.status("[bold yellow]Restarting services...", spinner="dots"):
        if run_command(command, verbose):
            console.print("[bold green]Services restarted successfully[/bold green]")

@cli.command('status')
@click.pass_context
def status(ctx):
    """Show status of all services"""
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'ps', '--format', 'json']
    verbose = ctx.obj.get('VERBOSE', False)
    
    with console.status("[bold blue]Fetching service status...", spinner="dots"):
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error:[/bold red] {result.stderr}")
            return
        
        try:
            # The output is one JSON object per line, not a JSON array
            services = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        service_data = json.loads(line)
                        services.append(service_data)
                    except json.JSONDecodeError:
                        continue
            
            if not services:
                console.print("[yellow]No running services found[/yellow]")
                return
            
            # Get the config to map services
            from .config import get_config
            config = get_config()
            config_services = config.get("services", {})
            
            # Create a mapping from container patterns to service keys
            container_pattern_to_service_key = {}
            for service_key, service_info in config_services.items():
                for pattern in service_info.get("container_patterns", []):
                    container_pattern_to_service_key[pattern] = service_key
                
            table = Table(title="Project Services")
            table.add_column("Service", style="cyan")
            table.add_column("Docker Service", style="blue")
            table.add_column("Status", style="green")
            table.add_column("Ports", style="yellow")
            
            for service in services:
                docker_service_name = service.get('Service', 'Unknown')
                container_name = service.get('Name', 'Unknown')
                status = service.get('Status', 'Unknown')
                ports = service.get('Ports', '')
                
                # Find the service key that matches this Docker service
                service_key = docker_service_name
                for pattern, key in container_pattern_to_service_key.items():
                    if pattern in docker_service_name:
                        service_key = key
                        break
                
                status_style = "green" if "Up" in status and "unhealthy" not in status else "red"
                table.add_row(
                    service_key,
                    container_name,
                    f"[{status_style}]{status}[/{status_style}]",
                    ports
                )
            
            console.print(table)
        except Exception as e:
            # Fallback to plain output
            console.print(f"[bold red]Error parsing JSON:[/bold red] {str(e)}")
            console.print("[yellow]Showing raw output:[/yellow]")
            console.print(result.stdout)



@cli.group('service')
@click.pass_context
def service_group(ctx):
    """Manage Docker services"""
    pass

@service_group.command('list')
@click.option('--project-prefix', '-p', help='Project prefix for filtering services')
@click.option('--debug', '-d', is_flag=True, help='Show debug information')
@click.pass_context
def service_list(ctx, project_prefix, debug):
    """List all running Docker services with URLs"""
    prefix = project_prefix or PROJECT_NAME
    verbose = ctx.obj.get('VERBOSE', False)
    
    list_services(prefix, verbose, debug)

@service_group.command('open')
@click.argument('service_identifier')
@click.pass_context
def service_open(ctx, service_identifier):
    """Open a service in the browser"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    open_service(PROJECT_NAME, service_identifier, verbose)

@cli.group('tool')
@click.pass_context
def tool_group(ctx):
    """Manage MCP (Model Context Protocol) tools"""
    pass

@tool_group.command('list')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def tool_list(ctx, verbose):
    """List all trusted MCP tools"""
    list_tools(verbose)

@tool_group.command('add')
@click.argument('server_name')
@click.option('--command', '-c', help='Command to run the MCP server (for Docker-based servers)')
@click.option('--args', '-a', multiple=True, help='Arguments for the command (can be used multiple times)')
@click.option('--env', '-e', multiple=True, help='Environment variables in KEY=VALUE format (can be used multiple times)')
@click.option('--type', '-t', type=click.Choice(['docker', 'cloud']), default='docker', help='Server type: docker (default) or cloud')
@click.option('--endpoint', help='Endpoint URL for cloud-hosted MCP servers')
@click.option('--version', help='Version of the MCP server')
@click.option('--description', help='Description of the MCP server')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing server configuration')
@click.pass_context
def tool_add(ctx, server_name, command, args, env, type, endpoint, version, description, force):
    """Add a new MCP tool to the configuration
    
    Add your own custom MCP servers to extend functionality.
    
    Examples:
    
    Add a custom Docker-based MCP server:
    weave tool add my-server --command docker --args run --args my-image:latest --env API_KEY=secret
    
    Add a cloud-hosted MCP server:
    weave tool add jira-cloud --type cloud --endpoint https://mcp.atlassian.com --env ATLASSIAN_API_TOKEN=your-token
    
    Add a filesystem tool with specific path:
    weave tool add my-files --command npx --args @modelcontextprotocol/server-filesystem --args /home/user/docs
    
    Add a Python-based MCP server:
    weave tool add my-python-tool --command python --args -m --args my_mcp_package --env CONFIG_PATH=/path/to/config
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    # Add custom tool
    if type == "cloud":
        if not endpoint:
            console.print("[red]--endpoint is required for cloud-hosted servers[/red]")
            return
    else:
        if not command:
            console.print("[red]--command is required for Docker-based servers[/red]")
            return
    
    # Parse environment variables
    env_dict = {}
    for env_var in env:
        if '=' not in env_var:
            console.print(f"[red]Invalid environment variable format: {env_var}. Use KEY=VALUE[/red]")
            return
        key, value = env_var.split('=', 1)
        env_dict[key] = value
    
    success = add_tool(
        server_name,
        command=command,
        args=list(args),
        env=env_dict,
        server_type=type,
        endpoint=endpoint,
        version=version,
        description=description,
        force=force
    )
    
    if success and verbose:
        if type == "cloud":
            console.print(f"[blue]Added cloud-hosted MCP server with endpoint: {endpoint}[/blue]")
        else:
            console.print(f"[blue]Added Docker-based MCP server with command: {command}[/blue]")

@tool_group.command('remove')
@click.argument('server_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def tool_remove(ctx, server_name, yes):
    """Remove an MCP tool from the configuration"""
    if not yes:
        if not click.confirm(f"Are you sure you want to remove '{server_name}'?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
    
    remove_tool(server_name)

@tool_group.command('install')
@click.argument('server_name')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed installation output')
@click.pass_context
def tool_install(ctx, server_name, verbose):
    """Test/install an MCP tool"""
    install_tool(server_name, verbose)



@tool_group.command('installed')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def tool_installed(ctx, verbose):
    """List MCP servers that are installed/configured
    
    This shows the servers that are actually installed and tracked in the weave config file,
    as opposed to 'list' which shows all available servers in the MCP config and 'popular' 
    which shows servers available for installation.
    """
    from .tools import get_weave_config
    
    verbose_flag = ctx.obj.get('VERBOSE', False) or verbose
    
    # Read from weave config instead of MCP config
    weave_config = get_weave_config()
    installed_tools = weave_config.get("mcp", {}).get("tools", {})
    
    if not installed_tools:
        console.print("[yellow]No MCP servers are currently installed/configured in weave.[/yellow]")
        console.print(f"[blue]Weave config file: {Path.cwd() / '.weave' / 'config.json'}[/blue]")
        console.print("[blue]Use 'weave tool add <server-name> --popular' to install popular tools[/blue]")
        console.print("[blue]Use 'weave tool popular' to see available tools[/blue]")
        return
    
    table = Table(title=f"Installed MCP Tools in Weave ({len(installed_tools)} configured)")
    table.add_column("Tool Name", style="cyan", no_wrap=True)
    table.add_column("Service", style="magenta", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("URL", style="yellow")
    
    if verbose_flag:
        table.add_column("Permissions", style="blue")
    
    for tool_name, tool_config in installed_tools.items():
        service = tool_config.get("service", "N/A")
        description = tool_config.get("description", "No description")
        url = tool_config.get("url", "Not configured")
        permissions = tool_config.get("permissions", [])
        
        row_data = [tool_name, service, description, url]
        
        if verbose_flag:
            perm_display = ", ".join(permissions) if permissions else "None"
            row_data.append(perm_display)
        
        table.add_row(*row_data)
    
    console.print(table)
    
    if verbose_flag:
        console.print(f"\n[blue]Weave config file: {Path.cwd() / '.weave' / 'config.json'}[/blue]")
        console.print(f"[blue]Total tools installed in weave: {len(installed_tools)}[/blue]")
        
        # Show services breakdown
        services = set(tool.get("service", "unknown") for tool in installed_tools.values())
        console.print(f"[blue]Services used: {', '.join(services)}[/blue]")

@tool_group.command('config')
@click.option('--path', '-p', help='Set the MCP configuration file path')
@click.option('--show', '-s', is_flag=True, help='Show current MCP configuration path')
@click.pass_context
def tool_config(ctx, path, show):
    """Configure MCP settings
    
    Examples:
    
    Show current MCP config path:
    weave tool config --show
    
    Set MCP config path:
    weave tool config --path /home/travisf/mcp.json
    weave tool config --path ~/.cursor/mcp.json
    """
    if show:
        current_path = get_mcp_config_path()
        console.print(f"[blue]Current MCP configuration path:[/blue] {current_path}")
        
        # Check if path exists
        if current_path.exists():
            console.print(f"[green]✓ Configuration file exists[/green]")
            try:
                with open(current_path, 'r') as f:
                    config = json.load(f)
                    server_count = len(config.get('mcpServers', {}))
                    console.print(f"[blue]Configured servers:[/blue] {server_count}")
            except Exception as e:
                console.print(f"[yellow]⚠ Error reading config: {e}[/yellow]")
        else:
            console.print(f"[yellow]⚠ Configuration file does not exist[/yellow]")
        return
    
    if path:
        # Expand user path (~) but keep relative paths relative
        if path.startswith('~'):
            config_path = Path(path).expanduser()
            path_to_store = str(config_path)
        else:
            config_path = Path(path)
            path_to_store = path
        
        # If it's a relative path, resolve it for validation but store the original
        if not config_path.is_absolute():
            resolved_path = Path.cwd() / config_path
        else:
            resolved_path = config_path
        
        # Validate the directory exists
        if not resolved_path.parent.exists():
            console.print(f"[red]Error: Directory {resolved_path.parent} does not exist[/red]")
            return
        
        # Set the path in weave config (store original path format)
        if set_mcp_config_path(path_to_store):
            console.print(f"[green]MCP configuration path updated successfully[/green]")
            
            # If the file doesn't exist, inform the user
            if not resolved_path.exists():
                console.print(f"[yellow]Configuration file doesn't exist at {resolved_path}[/yellow]")
                console.print("[yellow]Please create the configuration file manually or copy from an existing one[/yellow]")
        else:
            console.print(f"[red]Failed to update MCP configuration path[/red]")
    else:
        console.print("[yellow]Use --path to set the MCP configuration path or --show to display current path[/yellow]")
        console.print("[yellow]Example: weave tool config --path ~/.cursor/mcp.json[/yellow]") 