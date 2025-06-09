#!/usr/bin/env python

import os
import subprocess
import click
from rich.console import Console

from .config import get_project_name
from .docker_commands import run_command
from .services import get_rag_logs

console = Console()

# Project name to scope all operations
PROJECT_NAME = get_project_name()

@click.command('up')
@click.option('--detach', '-d', is_flag=True, help='Run in detached mode')
@click.option('--service', '-s', multiple=True, help='Specific service(s) to start')
@click.pass_context
def up(ctx, detach, service):
    """Start Docker Compose services"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'up']
    if detach:
        command.append('-d')
    if service:
        command.extend(service)
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

@click.command('down')
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes')
@click.option('--remove-orphans', is_flag=True, help='Remove containers for services not in the compose file')
@click.pass_context
def down(ctx, volumes, remove_orphans):
    """Stop Docker Compose services"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'down']
    if volumes:
        command.append('-v')
    if remove_orphans:
        command.append('--remove-orphans')
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

@click.command('logs')
@click.option('--follow', '-f', is_flag=True, help='Follow logs')
@click.option('--tail', '-n', default=100, help='Number of lines to show')
@click.argument('service', required=False)
@click.option('--verbose', '-v', is_flag=True, help='Show detailed logs without filtering')
@click.pass_context
def logs(ctx, follow, tail, service, verbose):
    """View logs for services"""
    ctx_verbose = ctx.obj.get('VERBOSE', False)
    
    # Special case for RAG logs
    if service == "rag":
        get_rag_logs(follow, tail, verbose or ctx_verbose)
        return
    
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'logs']
    if follow:
        command.append('-f')
    command.extend(['--tail', str(tail)])
    if service:
        command.append(service)
    
    if ctx_verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    # Filter out noisy logs unless verbose is specified
    if not verbose and not ctx_verbose:
        # Run with filtering
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            for line in iter(process.stdout.readline, ''):
                # Filter out common noisy patterns
                if any(pattern in line.lower() for pattern in [
                    'health check',
                    'healthcheck',
                    '/health',
                    'ping',
                    'heartbeat'
                ]):
                    continue
                print(line, end='')
            
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            console.print("\n[yellow]Logs interrupted by user[/yellow]")
    else:
        # Run without filtering
        run_command(command, ctx_verbose)

@click.command('restart')
@click.argument('service', required=False)
@click.pass_context
def restart(ctx, service):
    """Restart Docker Compose services"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'restart']
    if service:
        command.append(service)
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    run_command(command, verbose)

@click.command('status')
@click.pass_context
def status(ctx):
    """Show status of Docker Compose services"""
    verbose = ctx.obj.get('VERBOSE', False)
    
    command = ['docker', 'compose', '-p', PROJECT_NAME, 'ps']
    
    if verbose:
        console.print(f"[blue]Running: {' '.join(command)}[/blue]")
    
    with console.status("[bold blue]Fetching service status...", spinner="dots"):
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[bold red]Error:[/bold red] {result.stderr}")
            return
        
        # Parse and display the output in a more readable format
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Skip if only header
            console.print("[bold blue]Service Status:[/bold blue]")
            for line in lines:
                if line.strip():
                    # Color code based on status
                    if 'Up' in line:
                        console.print(f"[green]{line}[/green]")
                    elif 'Exit' in line or 'Down' in line:
                        console.print(f"[red]{line}[/red]")
                    else:
                        console.print(line)
        else:
            console.print("[yellow]No services are currently running[/yellow]") 