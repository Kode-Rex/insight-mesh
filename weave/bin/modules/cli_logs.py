#!/usr/bin/env python

import subprocess
import click
from rich.console import Console

from .config import get_project_name
from .services import get_rag_logs

console = Console()

@click.command('log')
@click.option('--follow', '-f', is_flag=True, help='Follow logs')
@click.option('--tail', '-n', default=100, help='Number of lines to show')
@click.argument('service', required=False, metavar='[SERVICE]')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed logs without filtering')
@click.pass_context
def logs(ctx, follow, tail, service, verbose):
    """View logs for services
    
    SERVICE can be any Docker Compose service name, or use the special service 'rag' 
    to view filtered RAG handler logs from the LiteLLM container.
    
    Examples:
    
    View all service logs:
    weave logs
    
    View logs for a specific service:
    weave logs litellm
    
    View RAG handler logs (filtered from LiteLLM):
    weave logs rag
    
    Follow RAG logs in real-time:
    weave logs rag --follow
    """
    # If no service specified and no flags provided, show help
    if not service and not follow and not verbose:
        click.echo(ctx.get_help())
        return
    
    project_name = get_project_name()
    ctx_verbose = ctx.obj.get('VERBOSE', False)
    
    # Special case for RAG logs
    if service == "rag":
        get_rag_logs(follow, tail, verbose or ctx_verbose)
        return
    
    command = ['docker', 'compose', '-p', project_name, 'logs']
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
        subprocess.run(command) 