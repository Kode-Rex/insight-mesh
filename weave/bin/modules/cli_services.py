#!/usr/bin/env python

import click
from rich.console import Console

from .services import list_services, open_service
from .config import get_project_name

console = Console()

@click.group('service', invoke_without_command=True)
@click.pass_context
def service_group(ctx):
    """Manage Docker services"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

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