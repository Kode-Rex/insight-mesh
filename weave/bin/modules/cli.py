#!/usr/bin/env python

import click
from rich.console import Console
from dotenv import load_dotenv

from .cli_docker import up, down, logs, restart, status
from .cli_services import service_group
from .cli_tools import tool_group

# Load environment variables
load_dotenv()

console = Console()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Weaver: A Rails-like framework for rapidly building and deploying enterprise-grade GenAI applications."""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose

# Add the imported commands and groups to the CLI
cli.add_command(up)
cli.add_command(down)
cli.add_command(logs)
cli.add_command(restart)
cli.add_command(status)
cli.add_command(service_group)
cli.add_command(tool_group)

if __name__ == '__main__':
    cli() 