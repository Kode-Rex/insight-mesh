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