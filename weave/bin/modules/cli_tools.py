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
@click.argument('command_or_url')
@click.option('--env', '-e', multiple=True, help='Environment variables in KEY=VALUE format')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing server configuration')
@click.pass_context
def tool_add(ctx, server_name, command_or_url, env, force):
    """Add a new MCP tool to the configuration
    
    COMMAND_OR_URL can be either:
    - A Docker image (e.g., my-image:latest)
    - A full command (e.g., "npx @modelcontextprotocol/server-filesystem /path")
    - A URL for cloud-hosted servers (e.g., https://api.example.com/mcp)
    
    Examples:
    
    Add a Docker image:
    weave tool add my-server my-image:latest --env API_KEY=secret
    
    Add a cloud-hosted server:
    weave tool add jira-cloud https://mcp.atlassian.com --env ATLASSIAN_API_TOKEN=your-token
    
    Add an NPX command:
    weave tool add my-files "npx @modelcontextprotocol/server-filesystem /home/user/docs"
    
    Add a Python module:
    weave tool add my-python-tool "python -m my_mcp_package" --env CONFIG_PATH=/path/to/config
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    # Parse environment variables
    env_dict = {}
    for env_var in env:
        if '=' not in env_var:
            console.print(f"[red]Invalid environment variable format: {env_var}. Use KEY=VALUE[/red]")
            return
        key, value = env_var.split('=', 1)
        env_dict[key] = value
    
    # Auto-detect type and parse command_or_url
    if command_or_url.startswith(('http://', 'https://')):
        # Cloud-hosted server
        server_type = "cloud"
        endpoint = command_or_url
        command = None
        args = []
        description = f"Cloud-hosted MCP server at {endpoint}"
    elif ' ' in command_or_url:
        # Full command with arguments
        server_type = "docker"
        command_parts = command_or_url.split()
        if command_parts[0] == "docker":
            # Already a docker command
            command = command_parts[0]
            args = command_parts[1:]
        else:
            # Wrap in docker run
            command = "docker"
            args = ["run", "-d", "--rm", "--name", f"mcp-{server_name}"] + command_parts
        endpoint = None
        description = f"Docker-based MCP server: {command_or_url}"
    else:
        # Assume it's a Docker image
        server_type = "docker"
        command = "docker"
        args = ["run", "-d", "--rm", "--name", f"mcp-{server_name}", command_or_url]
        endpoint = None
        description = f"Docker MCP server using image: {command_or_url}"
    
    success = add_tool(
        server_name,
        command=command,
        args=args,
        env=env_dict,
        server_type=server_type,
        endpoint=endpoint,
        version="latest",
        description=description,
        force=force
    )
    
    if success and verbose:
        if server_type == "cloud":
            console.print(f"[blue]Added cloud-hosted MCP server: {endpoint}[/blue]")
        else:
            console.print(f"[blue]Added Docker MCP server: {command_or_url}[/blue]")

@tool_group.command('remove')
@click.argument('server_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def tool_remove(ctx, server_name, yes):
    """Remove an MCP tool from the configuration"""
    if not yes:
        if not click.confirm(f"Are you sure you want to remove '{server_name}'?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
    
    remove_tool(server_name)

@tool_group.command('install')
@click.argument('server_name')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed installation output')
@click.pass_context
def tool_install(ctx, server_name, verbose):
    """Test/install an MCP tool"""
    install_tool(server_name, verbose)

@tool_group.command('list')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def tool_list(ctx, verbose):
    """List MCP servers that are installed/configured
    
    This shows the servers that are actually installed and tracked in the weave config file,
    as opposed to 'trusted' which shows all available servers in the MCP config.
    """
    verbose_flag = ctx.obj.get('VERBOSE', False) or verbose
    
    # Read from weave config instead of MCP config
    weave_config = get_weave_config()
    installed_tools = weave_config.get("mcp", {}).get("tools", {})
    
    if not installed_tools:
        console.print("[yellow]No MCP servers are currently installed/configured in weave.[/yellow]")
        console.print(f"[blue]Weave config file: {Path.cwd() / '.weave' / 'config.json'}[/blue]")
        console.print("[blue]Use 'weave tool add <server-name>' to add tools[/blue]")
        console.print("[blue]Use 'weave tool trusted' to see available tools[/blue]")
        return
    
    table = Table(title=f"Installed MCP Tools in Weave ({len(installed_tools)} configured)")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Service", style="magenta", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("URL", style="yellow")
    
    if verbose_flag:
        table.add_column("Permissions", style="blue")
    
    for tool_name, tool_config in installed_tools.items():
        service = tool_config.get("service", "N/A")
        description = tool_config.get("description", "No description")
        url = tool_config.get("url", "Not configured")
        permissions = tool_config.get("permissions", [])
        
        row_data = [tool_name, service, description, url]
        
        if verbose_flag:
            perm_display = ", ".join(permissions) if permissions else "None"
            row_data.append(perm_display)
        
        table.add_row(*row_data)
    
    console.print(table)
    
    if verbose_flag:
        console.print(f"\n[blue]Weave config file: {Path.cwd() / '.weave' / 'config.json'}[/blue]")
        console.print(f"[blue]Total tools installed in weave: {len(installed_tools)}[/blue]")
        
        # Show services breakdown
        services = set(tool.get("service", "unknown") for tool in installed_tools.values())
        console.print(f"[blue]Services used: {', '.join(services)}[/blue]")

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