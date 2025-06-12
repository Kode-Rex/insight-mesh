#!/usr/bin/env python

import click
from rich.console import Console

console = Console()

@click.group('tool', invoke_without_command=True)
@click.pass_context
def db_tool_group(ctx):
    """Manage database migration tools"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@db_tool_group.command('install')
@click.option('--force', is_flag=True, help='Force reinstall even if tools are available')
@click.pass_context
def db_tools_install(ctx, force):
    """Install migration tools automatically
    
    This command will:
    1. Check for required migration tools
    2. Install missing Python dependencies via pip
    3. Install neo4j-migrations CLI tool via package managers
    4. Provide manual installation instructions if needed
    
    Examples:
    
    Check and install missing tools:
    weave db tool install
    
    Force reinstall all tools:
    weave db tool install --force
    """
    from .cli_migrate import check_and_install_tools, install_python_dependencies, install_neo4j_migrations
    
    if force:
        console.print("[blue]🔄 Force installing all migration tools...[/blue]")
        success = True
        success &= install_python_dependencies()
        success &= install_neo4j_migrations()
        
        if success:
            console.print("[green]🎉 All tools installed successfully![/green]")
        else:
            console.print("[yellow]⚠️  Some tools may require manual installation[/yellow]")
    else:
        check_and_install_tools()

@db_tool_group.command('check')
@click.pass_context
def db_tools_check(ctx):
    """Check availability of migration tools
    
    This command will check if all required migration tools are available:
    - Python dependencies (requests, psycopg2, etc.)
    - neo4j-migrations CLI tool
    - Java (required for neo4j-migrations)
    
    Examples:
    
    Check tool availability:
    weave db tool check
    """
    from .cli_migrate import check_and_install_tools
    
    # Run check without offering to install
    console.print("[blue]🔍 Checking migration tools availability...[/blue]")
    
    tools_status = {}
    
    # Check Python dependencies
    try:
        import requests
        import psycopg2
        import alembic
        tools_status['python_deps'] = True
        console.print("[green]✅ Python dependencies: Available[/green]")
    except ImportError as e:
        tools_status['python_deps'] = False
        console.print(f"[red]❌ Python dependencies: Missing ({e})[/red]")
    
    # Check Java
    try:
        import subprocess
        java_result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if java_result.returncode == 0:
            tools_status['java'] = True
            # Java -version outputs to stderr
            version_info = java_result.stderr.split('\n')[0] if java_result.stderr else 'version unknown'
            console.print(f"[green]✅ Java: Available ({version_info})[/green]")
        else:
            tools_status['java'] = False
            console.print("[red]❌ Java: Not working properly[/red]")
    except FileNotFoundError:
        tools_status['java'] = False
        console.print("[red]❌ Java: Not installed[/red]")
    
    # Check neo4j-migrations
    try:
        import subprocess
        result = subprocess.run(['neo4j-migrations', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            tools_status['neo4j_migrations'] = True
            version = result.stdout.strip()
            console.print(f"[green]✅ neo4j-migrations: Available ({version})[/green]")
        else:
            tools_status['neo4j_migrations'] = False
            console.print("[red]❌ neo4j-migrations: Not working properly[/red]")
    except FileNotFoundError:
        tools_status['neo4j_migrations'] = False
        console.print("[red]❌ neo4j-migrations: Not installed[/red]")
    
    # Summary
    available_count = sum(1 for status in tools_status.values() if status)
    total_count = len(tools_status)
    
    if available_count == total_count:
        console.print(f"\n[green]🎉 All tools available ({available_count}/{total_count})[/green]")
    else:
        console.print(f"\n[yellow]⚠️  {available_count}/{total_count} tools available[/yellow]")
        console.print("[blue]💡 Run 'weave db tool install' to install missing tools[/blue]") 