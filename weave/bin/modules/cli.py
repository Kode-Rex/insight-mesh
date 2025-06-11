#!/usr/bin/env python

import click
import sys
import os
from rich.console import Console
from dotenv import load_dotenv
import importlib.util
import glob
from pathlib import Path

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
    __version__ = "0.1.3"  # Fallback to known version

def load_python_modules_from_dir(directory_path: str):
    """Load all Python modules from a directory"""
    if not os.path.exists(directory_path):
        return
    
    for py_file in glob.glob(os.path.join(directory_path, "*.py")):
        if os.path.basename(py_file) == "__init__.py":
            continue
        
        module_name = os.path.splitext(os.path.basename(py_file))[0]
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

# Load domain, context, tool, and agent definitions from .weave directory
weave_dir = os.path.join(os.getcwd(), ".weave")
if os.path.exists(weave_dir):
    load_python_modules_from_dir(os.path.join(weave_dir, "domains"))
    load_python_modules_from_dir(os.path.join(weave_dir, "contexts"))
    load_python_modules_from_dir(os.path.join(weave_dir, "tools"))
    load_python_modules_from_dir(os.path.join(weave_dir, "agents"))

# Domain commands
@click.group()
def domain():
    """Manage domains"""
    pass

@domain.command()
def list():
    """List all domains"""
    try:
        from weave.domains import get_all_domains
        domains = get_all_domains()
        if domains:
            console.print("[bold blue]Available Domains:[/bold blue]")
            for name, domain_obj in domains.items():
                console.print(f"  • [green]{name}[/green]: {domain_obj.description}")
        else:
            console.print("[yellow]No domains found[/yellow]")
    except ImportError:
        console.print("[red]Domain system not available[/red]")

@click.group()
def context():
    """Manage contexts"""
    pass

@context.command()
def list():
    """List all contexts"""
    try:
        from weave.domains import get_all_contexts
        contexts = get_all_contexts()
        if contexts:
            console.print("[bold blue]Available Contexts:[/bold blue]")
            for name, context_obj in contexts.items():
                console.print(f"  • [green]{name}[/green]: {context_obj.description}")
        else:
            console.print("[yellow]No contexts found[/yellow]")
    except ImportError:
        console.print("[red]Context system not available[/red]")

@click.group()
def agent():
    """Manage agents"""
    pass

@agent.command()
def list():
    """List all agents"""
    try:
        from weave.agents import get_all_agents
        agents = get_all_agents()
        if agents:
            console.print("[bold blue]Available Agents:[/bold blue]")
            for name, agent_cls in agents.items():
                agent_obj = agent_cls()
                console.print(f"  • [green]{name}[/green]: {agent_obj.description}")
        else:
            console.print("[yellow]No agents found[/yellow]")
    except ImportError:
        console.print("[red]Agent system not available[/red]")

@agent.command()
@click.argument('agent_name')
@click.option('--user-id', required=True, help='User ID for context')
@click.option('--query', required=True, help='Query to process')
def run(agent_name, user_id, query):
    """Run an agent"""
    try:
        from weave.agents import get_agent
        import asyncio
        
        agent_cls = get_agent(agent_name)
        if not agent_cls:
            console.print(f"[red]Agent '{agent_name}' not found[/red]")
            return
        
        console.print(f"[blue]Running agent:[/blue] {agent_name}")
        console.print(f"[blue]User ID:[/blue] {user_id}")
        console.print(f"[blue]Query:[/blue] {query}")
        
        # Create agent instance with user_id and run
        agent_obj = agent_cls(user_id=user_id)
        result = asyncio.run(agent_obj.execute(query))
        
        console.print("[green]Result:[/green]")
        console.print(f"  {result}")
            
    except ImportError:
        console.print("[red]Agent system not available[/red]")
    except Exception as e:
        console.print(f"[red]Error running agent: {e}[/red]")

@click.group()
def schema():
    """Manage schemas"""
    pass

@schema.command()
@click.argument('domain_name')
def show(domain_name):
    """Show schema for a domain"""
    try:
        from weave.domains import get_domain
        domain_obj = get_domain(domain_name)
        if domain_obj:
            console.print(f"[bold blue]Schema for domain '{domain_name}':[/bold blue]")
            schemas = domain_obj.schemas
            for db_type, schema_info in schemas.items():
                console.print(f"  [green]{db_type}[/green]: {schema_info}")
        else:
            console.print(f"[red]Domain '{domain_name}' not found[/red]")
    except ImportError:
        console.print("[red]Domain system not available[/red]")

@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--version', is_flag=True, help='Show version and exit')
@click.pass_context
def cli(ctx, verbose, version):
    """Weaver: A Rails-like framework for rapidly building and deploying enterprise-grade GenAI applications."""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    
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
cli.add_command(domain)
cli.add_command(context)
cli.add_command(agent)
cli.add_command(schema)

if __name__ == '__main__':
    cli() 