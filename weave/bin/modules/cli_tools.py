#!/usr/bin/env python

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path

from .tools import list_tools, add_tool, remove_tool, install_tool, set_mcp_config_path, get_mcp_config_path, check_tool_availability, get_weave_config

console = Console()

@click.group('tool', invoke_without_command=True)
@click.pass_context
def tool_group(ctx):
    """Manage MCP (Model Context Protocol) tools"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@tool_group.command('trusted')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def tool_trusted(ctx, verbose):
    """List all trusted MCP tools"""
    list_tools(verbose)

@tool_group.command('add')
@click.argument('server_name')
@click.argument('url')
@click.option('--transport', default='sse', type=click.Choice(['sse', 'http']), help='Transport type (sse or http)')
@click.option('--auth-type', type=click.Choice(['none', 'api_key', 'bearer_token', 'basic']), help='Authentication type')
@click.option('--spec-version', default='2024-11-05', help='MCP spec version')
@click.option('--description', help='Server description')
@click.option('--scope', default='all', type=click.Choice(['rag', 'agent', 'all']), help='Server scope (rag, agent, or all)')
@click.option('--env', '-e', multiple=True, help='Environment variables in KEY=VALUE format')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing server')
@click.pass_context
def tool_add(ctx, server_name, url, transport, auth_type, spec_version, description, scope, env, force):
    """Add MCP server to weave config
    
    Examples:
    
    Add WebCat server:
    weave tool add webcat http://webcat:8765/mcp --description "Web search tool"
    
    Add with environment variables:
    weave tool add webcat http://webcat:8765/mcp --env API_KEY=secret --env TIMEOUT=30
    
    Add with authentication:
    weave tool add secure-api https://api.example.com/mcp --auth-type bearer_token --env BEARER_TOKEN=your-token
    """
    from .mcp_config import add_mcp_server_to_config
    
    # Parse environment variables
    env_dict = {}
    for env_var in env:
        if '=' not in env_var:
            console.print(f"[red]Invalid environment variable format: {env_var}. Use KEY=VALUE[/red]")
            return
        key, value = env_var.split('=', 1)
        env_dict[key] = value
    
    success = add_mcp_server_to_config(
        server_name=server_name,
        url=url,
        transport=transport,
        auth_type=auth_type,
        spec_version=spec_version,
        description=description or f"MCP server at {url}",
        env_vars=env_dict,
        scope=scope,
        force=force
    )
    
    if success:
        console.print(f"[green]✅ Added MCP server '{server_name}' to weave config[/green]")
        console.print("[blue]💡 Server is now available via the registry API and RAG hooks[/blue]")
    else:
        console.print(f"[red]❌ Failed to add MCP server '{server_name}'[/red]")

@tool_group.command('remove')
@click.argument('server_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def tool_remove(ctx, server_name, yes):
    """Remove MCP server from weave config"""
    from .mcp_config import remove_mcp_server_from_config
    
    if not yes:
        if not click.confirm(f"Are you sure you want to remove MCP server '{server_name}'?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
    
    success = remove_mcp_server_from_config(server_name)
    
    if success:
        console.print(f"[green]✅ Removed MCP server '{server_name}' from weave config[/green]")
        console.print("[blue]💡 Server is no longer available via the registry API and RAG hooks[/blue]")
    else:
        console.print(f"[red]❌ Failed to remove MCP server '{server_name}'[/red]")

@tool_group.command('list')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def tool_list(ctx, verbose):
    """List MCP servers in weave config"""
    from .mcp_config import list_mcp_servers_from_config
    
    verbose_flag = ctx.obj.get('VERBOSE', False) or verbose
    list_mcp_servers_from_config(verbose=verbose_flag)

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
                import json
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





@tool_group.command('test-registry')
@click.option('--registry-url', default='http://localhost:8888', help='MCP Registry URL')
@click.pass_context
def tool_test_registry(ctx, registry_url):
    """Test the MCP configuration registry server"""
    import requests
    from rich.json import JSON
    
    console.print(f"[blue]Testing MCP Registry at: {registry_url}[/blue]")
    
    try:
        # Test health check
        console.print("\n[yellow]1. Testing health check...[/yellow]")
        response = requests.get(f"{registry_url}/health", timeout=10)
        if response.status_code == 200:
            console.print("[green]✓ Health check passed[/green]")
            console.print(JSON.from_data(response.json()))
        else:
            console.print(f"[red]✗ Health check failed: {response.status_code}[/red]")
            return
        
        # Test get all servers
        console.print("\n[yellow]2. Testing get all servers...[/yellow]")
        response = requests.get(f"{registry_url}/servers", timeout=10)
        if response.status_code == 200:
            servers = response.json()
            console.print(f"[green]✓ Found {len(servers)} servers[/green]")
            console.print(JSON.from_data(servers))
        else:
            console.print(f"[red]✗ Failed to get servers: {response.status_code}[/red]")
            
        # Test get RAG servers
        console.print("\n[yellow]3. Testing get RAG servers...[/yellow]")
        response = requests.get(f"{registry_url}/servers/rag", timeout=10)
        if response.status_code == 200:
            rag_servers = response.json()
            console.print(f"[green]✓ Found {len(rag_servers)} RAG servers[/green]")
            console.print(JSON.from_data(rag_servers))
        else:
            console.print(f"[red]✗ Failed to get RAG servers: {response.status_code}[/red]")
            
        # Test get full config
        console.print("\n[yellow]4. Testing get full config...[/yellow]")
        response = requests.get(f"{registry_url}/config", timeout=10)
        if response.status_code == 200:
            config = response.json()
            console.print("[green]✓ Config retrieved successfully[/green]")
            console.print(f"[blue]Config path: {config.get('config_path')}[/blue]")
            console.print(f"[blue]Last modified: {config.get('last_modified')}[/blue]")
            console.print(f"[blue]Total servers: {len(config.get('servers', {}))}[/blue]")
        else:
            console.print(f"[red]✗ Failed to get config: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Could not connect to registry at {registry_url}[/red]")
        console.print("[yellow]Make sure the mcp-registry service is running[/yellow]")
    except requests.exceptions.Timeout:
        console.print(f"[red]✗ Timeout connecting to registry at {registry_url}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error testing registry: {str(e)}[/red]")

 