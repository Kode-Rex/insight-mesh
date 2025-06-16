#!/usr/bin/env python

import click
import sys
import os
from rich.console import Console
from dotenv import load_dotenv

from .cli_logs import log
from .cli_services import service_group
from .cli_tools import tool_group
from .cli_db import db_group

# Load environment variables
load_dotenv()

console = Console()

# Import version from the weave package
try:
    # Add the parent directory to the path to find the weave package
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from weave import __version__
except ImportError:
    __version__ = "0.1.5"  # Fallback to known version

@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--version', is_flag=True, help='Show version and exit')
@click.option('--test-mode', is_flag=True, help='Enable test mode (simulates commands without executing)')
@click.pass_context
def cli(ctx, verbose, version, test_mode):
    """Weaver: A Rails-like framework for rapidly building and deploying enterprise-grade GenAI applications."""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    ctx.obj['TEST_MODE'] = test_mode or os.getenv('WEAVE_TEST_MODE', '').lower() in ['true', '1', 'yes']
    
    if ctx.obj['TEST_MODE']:
        console.print("[yellow]🧪 TEST MODE ENABLED - Commands will be simulated[/yellow]")
    
    if version:
        console.print(f"[bold blue]Weave[/bold blue] version [green]{__version__}[/green]")
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Add the imported commands and groups to the CLI
cli.add_command(log)
cli.add_command(service_group)
cli.add_command(tool_group)
cli.add_command(db_group)

if __name__ == '__main__':
    cli() 