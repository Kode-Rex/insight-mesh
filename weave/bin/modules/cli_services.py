#!/usr/bin/env python

import os
import subprocess
import click
from rich.console import Console

from .services import list_services, open_service, get_rag_logs
from .config import get_project_name
from .docker_commands import run_command

console = Console()

@click.group('service', invoke_without_command=True)
@click.pass_context
def service_group(ctx):
    """Manage Docker services"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@service_group.command('add')
@click.argument('service_name')
@click.argument('image')
@click.option('--port', '-p', multiple=True, help='Port mappings in HOST:CONTAINER format')
@click.option('--env', '-e', multiple=True, help='Environment variables in KEY=VALUE format')
@click.option('--volume', '-v', multiple=True, help='Volume mappings in HOST:CONTAINER format')
@click.option('--depends-on', multiple=True, help='Services this service depends on')
@click.option('--restart', default='unless-stopped', help='Restart policy (default: unless-stopped)')
@click.option('--description', help='Description of the service')
@click.option('--display-name', help='Human-readable display name for the service')
@click.pass_context
def service_add(ctx, service_name, image, port, env, volume, depends_on, restart, description, display_name):
    """Add a new service to docker-compose.yml and .weave/config.json"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    # Check if docker-compose.yml exists
    compose_file = 'docker-compose.yml'
    if not os.path.exists(compose_file):
        console.print(f"[red]Error: {compose_file} not found in current directory[/red]")
        return
    
    # Check if .weave/config.json exists
    config_file = '.weave/config.json'
    if not os.path.exists(config_file):
        console.print(f"[red]Error: {config_file} not found[/red]")
        return
    
    # Read existing docker-compose.yml
    try:
        import yaml
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
    except ImportError:
        console.print("[red]Error: PyYAML is required to modify docker-compose.yml[/red]")
        console.print("[blue]Install with: pip install PyYAML[/blue]")
        return
    except Exception as e:
        console.print(f"[red]Error reading {compose_file}: {e}[/red]")
        return
    
    # Read existing .weave/config.json
    try:
        import json
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading {config_file}: {e}[/red]")
        return
    
    # Initialize services section if it doesn't exist
    if 'services' not in compose_data:
        compose_data['services'] = {}
    if 'services' not in config_data:
        config_data['services'] = {}
    
    # Check if service already exists
    if service_name in compose_data['services']:
        console.print(f"[yellow]Service '{service_name}' already exists in docker-compose.yml[/yellow]")
        return
    
    if service_name in config_data['services']:
        console.print(f"[yellow]Service '{service_name}' already exists in .weave/config.json[/yellow]")
        return
    
    # Build service configuration for docker-compose.yml
    service_config = {
        'image': image,
        'restart': restart
    }
    
    # Add ports if specified
    if port:
        service_config['ports'] = list(port)
    
    # Add environment variables if specified
    if env:
        service_config['environment'] = list(env)
    
    # Add volumes if specified
    if volume:
        service_config['volumes'] = list(volume)
    
    # Add dependencies if specified
    if depends_on:
        service_config['depends_on'] = list(depends_on)
    
    # Add the service to compose data
    compose_data['services'][service_name] = service_config
    
    # Build service configuration for .weave/config.json
    weave_service_config = {
        'display_name': display_name or service_name.replace('-', ' ').replace('_', ' ').title(),
        'description': description or f"Service running {image}",
        'images': [image],
        'container_patterns': [service_name]
    }
    
    # Add the service to config data
    config_data['services'][service_name] = weave_service_config
    
    # Write back to docker-compose.yml
    try:
        with open(compose_file, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
        
        console.print(f"[green]Successfully added service '{service_name}' to {compose_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error writing to {compose_file}: {e}[/red]")
        return
    
    # Write back to .weave/config.json
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        
        console.print(f"[green]Successfully added service '{service_name}' to {config_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error writing to {config_file}: {e}[/red]")
        return
    
    # Show summary
    if verbose:
        console.print(f"[blue]Service configuration:[/blue]")
        console.print(f"  Name: {service_name}")
        console.print(f"  Display Name: {weave_service_config['display_name']}")
        console.print(f"  Description: {weave_service_config['description']}")
        console.print(f"  Image: {image}")
        if port:
            console.print(f"  Ports: {', '.join(port)}")
        if env:
            console.print(f"  Environment: {', '.join(env)}")
        if volume:
            console.print(f"  Volumes: {', '.join(volume)}")
        if depends_on:
            console.print(f"  Depends on: {', '.join(depends_on)}")
        console.print(f"  Restart policy: {restart}")
    
    console.print(f"[blue]Run 'weave service up {service_name}' to start the service[/blue]")

@service_group.command('list')
@click.option('--project-prefix', '-p', help='Project prefix for filtering services')
@click.option('--debug', '-d', is_flag=True, help='Show debug information')
@click.pass_context
def service_list(ctx, project_prefix, debug):
    """List all running Docker services with URLs"""
    project_name = get_project_name()
    prefix = project_prefix or project_name
    verbose = ctx.obj.get('VERBOSE', False)
    
    list_services(prefix, verbose, debug)

@service_group.command('open')
@click.argument('service_identifier')
@click.pass_context
def service_open(ctx, service_identifier):
    """Open a service in the browser"""
    project_name = get_project_name()
    verbose = ctx.obj.get('VERBOSE', False)
    
    open_service(project_name, service_identifier, verbose)

@service_group.command('up')
@click.option('--detach', '-d', is_flag=True, help='Run in detached mode')
@click.option('--service', '-s', multiple=True, help='Specific service(s) to start')
@click.pass_context
def service_up(ctx, detach, service):
    """Start Docker Compose services"""
    project_name = get_project_name()
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', project_name, 'up']
    if detach:
        command.append('-d')
    if service:
        command.extend(service)
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

@service_group.command('down')
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes')
@click.option('--remove-orphans', is_flag=True, help='Remove containers for services not in the compose file')
@click.pass_context
def service_down(ctx, volumes, remove_orphans):
    """Stop Docker Compose services"""
    project_name = get_project_name()
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', project_name, 'down']
    if volumes:
        command.append('-v')
    if remove_orphans:
        command.append('--remove-orphans')
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

@service_group.command('restart')
@click.argument('service', required=False)
@click.pass_context
def service_restart(ctx, service):
    """Restart Docker Compose services"""
    project_name = get_project_name()
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', project_name, 'restart']
    if service:
        command.append(service)
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

 