#!/usr/bin/env python

import os
import json
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

def get_weave_config():
    """Load the weave configuration"""
    try:
        weave_config_path = Path.cwd() / '.weave' / 'config.json'
        if weave_config_path.exists():
            with open(weave_config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load weave config: {e}[/yellow]")
    return {}

def save_weave_config(config):
    """Save the weave configuration"""
    try:
        weave_config_path = Path.cwd() / '.weave' / 'config.json'
        weave_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(weave_config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        console.print(f"[red]Error saving weave config: {e}[/red]")
        return False

def get_mcp_config_path():
    """Get the MCP configuration file path, checking weave config first, then defaults"""
    # First check weave configuration
    weave_config = get_weave_config()
    
    # Check if MCP config path is set in weave config
    if 'mcp' in weave_config and 'config_path' in weave_config['mcp']:
        configured_path = weave_config['mcp']['config_path']
        
        # Handle relative paths - resolve relative to current working directory
        if not os.path.isabs(configured_path):
            return Path.cwd() / configured_path
        else:
            return Path(configured_path).expanduser()
    
    # Check for user-specified path in environment variable
    if 'MCP_CONFIG_PATH' in os.environ:
        return Path(os.environ['MCP_CONFIG_PATH'])
    
    # Default locations to check
    default_paths = [
        Path.home() / 'mcp.json',
        Path.home() / '.cursor' / 'mcp.json',
        Path('/home/travisf/mcp.json'),  # User's specific path
        Path.cwd() / '.cursor' / 'mcp.json',
        Path.cwd() / 'mcp.json'
    ]
    
    for path in default_paths:
        if path.exists():
            return path
    
    # Return the default user home path if none exist
    return Path.home() / 'mcp.json'

def set_mcp_config_path(config_path):
    """Set the MCP configuration path in weave config"""
    weave_config = get_weave_config()
    
    if 'mcp' not in weave_config:
        weave_config['mcp'] = {}
    
    # Store the path as provided (can be relative or absolute)
    weave_config['mcp']['config_path'] = str(config_path)
    
    if save_weave_config(weave_config):
        console.print(f"[green]MCP configuration path set to: {config_path}[/green]")
        return True
    else:
        console.print(f"[red]Failed to save MCP configuration path[/red]")
        return False

def load_mcp_config():
    """Load MCP configuration from JSON file"""
    config_path = get_mcp_config_path()
    
    if not config_path.exists():
        console.print(f"[yellow]MCP configuration file not found at {config_path}[/yellow]")
        console.print("[yellow]Creating a sample configuration file...[/yellow]")
        create_sample_config(config_path)
        return {"mcpServers": {}}
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing MCP configuration file: {e}[/red]")
        return {"mcpServers": {}}
    except Exception as e:
        console.print(f"[red]Error reading MCP configuration file: {e}[/red]")
        return {"mcpServers": {}}

def save_mcp_config(config):
    """Save MCP configuration to JSON file"""
    config_path = get_mcp_config_path()
    
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[red]Error saving MCP configuration file: {e}[/red]")
        return False

def create_sample_config(config_path):
    """Create a sample MCP configuration file with Docker-based FastMCP servers"""
    sample_config = {
        "mcpServers": {
            "webcat": {
                "command": "docker",
                "args": ["run", "--rm", "-i", "tmfrisinger/webcat:latest"],
                "env": {
                    "WEBCAT_URL": "http://localhost:8080"
                }
            },
            "mcp-server": {
                "command": "docker",
                "args": ["run", "--rm", "-i", "mcp:latest"],
                "env": {}
            },
            "filesystem-docker": {
                "command": "docker",
                "args": ["run", "--rm", "-i", "-v", "/tmp:/workspace", "fastmcp/filesystem:latest"],
                "env": {}
            }
        }
    }
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        console.print(f"[green]Sample Docker FastMCP configuration created at {config_path}[/green]")
        console.print("[yellow]All tools are Docker-based FastMCP SSE servers.[/yellow]")
        console.print("[yellow]Please edit the configuration file to customize Docker images and environment variables.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error creating sample configuration: {e}[/red]")

def list_tools(verbose=False):
    """List all available MCP tools from configuration"""
    config = load_mcp_config()
    servers = config.get("mcpServers", {})
    
    if not servers:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print(f"[yellow]Configuration file location: {get_mcp_config_path()}[/yellow]")
        return
    
    table = Table(title="Available MCP Tools")
    table.add_column("Server Name", style="cyan", no_wrap=True)
    table.add_column("Command", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Environment Variables", style="blue")
    
    for server_name, server_config in servers.items():
        command = server_config.get("command", "N/A")
        args = server_config.get("args", [])
        env_vars = server_config.get("env", {})
        
        # Build full command string
        full_command = f"{command} {' '.join(args)}" if args else command
        
        # Check if tool is available
        status = check_tool_availability(command, args)
        
        # Format environment variables
        env_display = ", ".join([f"{k}={'***' if 'key' in k.lower() or 'token' in k.lower() else v}" 
                                for k, v in env_vars.items()]) if env_vars else "None"
        
        table.add_row(
            server_name,
            full_command,
            status,
            env_display
        )
    
    console.print(table)
    
    if verbose:
        console.print(f"\n[blue]Configuration file: {get_mcp_config_path()}[/blue]")
        console.print(f"[blue]Total servers configured: {len(servers)}[/blue]")

def check_tool_availability(command, args):
    """Check if a tool is available and can be executed"""
    try:
        # For Docker commands, check if Docker is available and running
        if command == "docker":
            # First check if Docker is installed
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return "[red]Docker not installed[/red]"
            
            # Then check if Docker daemon is running
            result = subprocess.run(["docker", "info"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "[green]Available[/green]"
            else:
                return "[yellow]Docker installed but not running[/yellow]"
        
        # For other commands, check if they exist
        else:
            result = subprocess.run([command, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "[green]Available[/green]"
            else:
                return "[yellow]Unknown[/yellow]"
    
    except subprocess.TimeoutExpired:
        return "[yellow]Timeout[/yellow]"
    except FileNotFoundError:
        return "[red]Not found[/red]"
    except Exception:
        return "[yellow]Unknown[/yellow]"

def add_tool(server_name, command, args=None, env=None, force=False):
    """Add a new MCP tool to the configuration"""
    config = load_mcp_config()
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Check if server already exists
    if server_name in config["mcpServers"] and not force:
        console.print(f"[yellow]Server '{server_name}' already exists. Use --force to overwrite.[/yellow]")
        return False
    
    # Build server configuration
    server_config = {
        "command": command,
        "args": args or [],
        "env": env or {}
    }
    
    config["mcpServers"][server_name] = server_config
    
    if save_mcp_config(config):
        console.print(f"[green]Successfully added MCP server '{server_name}'[/green]")
        
        # Show the added configuration
        panel_content = f"""
[cyan]Server Name:[/cyan] {server_name}
[cyan]Command:[/cyan] {command}
[cyan]Arguments:[/cyan] {' '.join(args) if args else 'None'}
[cyan]Environment Variables:[/cyan] {len(env or {})} configured
        """
        
        console.print(Panel(panel_content.strip(), title="Added MCP Server", border_style="green"))
        return True
    else:
        return False

def remove_tool(server_name):
    """Remove an MCP tool from the configuration"""
    config = load_mcp_config()
    
    if "mcpServers" not in config or server_name not in config["mcpServers"]:
        console.print(f"[red]Server '{server_name}' not found in configuration.[/red]")
        return False
    
    del config["mcpServers"][server_name]
    
    if save_mcp_config(config):
        console.print(f"[green]Successfully removed MCP server '{server_name}'[/green]")
        return True
    else:
        return False

def install_tool(server_name, verbose=False):
    """Install/test an MCP tool by running it"""
    config = load_mcp_config()
    servers = config.get("mcpServers", {})
    
    if server_name not in servers:
        console.print(f"[red]Server '{server_name}' not found in configuration.[/red]")
        console.print("[yellow]Available servers:[/yellow]")
        for name in servers.keys():
            console.print(f"  - {name}")
        return False
    
    server_config = servers[server_name]
    command = server_config.get("command")
    args = server_config.get("args", [])
    env_vars = server_config.get("env", {})
    
    console.print(f"[blue]Installing/testing MCP server: {server_name}[/blue]")
    
    # Prepare environment
    env = os.environ.copy()
    env.update(env_vars)
    
    # Build command
    full_command = [command] + args
    
    if verbose:
        console.print(f"[blue]Command: {' '.join(full_command)}[/blue]")
        console.print(f"[blue]Environment variables: {list(env_vars.keys())}[/blue]")
    
    try:
        with console.status(f"[bold green]Testing {server_name}...", spinner="dots"):
            # For npx commands, we might want to just check if the package can be resolved
            if command == "npx" and args:
                # Try to get help or version info
                test_command = [command, "--yes"] + args + ["--help"]
                result = subprocess.run(test_command, 
                                      capture_output=True, text=True, 
                                      timeout=30, env=env)
                
                if result.returncode == 0:
                    console.print(f"[green]✓ MCP server '{server_name}' is working correctly[/green]")
                    if verbose:
                        console.print(f"[dim]Output: {result.stdout[:200]}...[/dim]")
                    return True
                else:
                    console.print(f"[red]✗ MCP server '{server_name}' failed to start[/red]")
                    if verbose:
                        console.print(f"[red]Error: {result.stderr}[/red]")
                    return False
            else:
                # For other commands, try to run with --help
                test_command = full_command + ["--help"]
                result = subprocess.run(test_command, 
                                      capture_output=True, text=True, 
                                      timeout=10, env=env)
                
                if result.returncode == 0:
                    console.print(f"[green]✓ MCP server '{server_name}' is available[/green]")
                    return True
                else:
                    console.print(f"[yellow]? MCP server '{server_name}' status unclear[/yellow]")
                    return True  # Don't fail for unclear status
    
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⚠ MCP server '{server_name}' test timed out[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error testing MCP server '{server_name}': {e}[/red]")
        return False

def get_popular_tools():
    """Get a list of popular Docker-based FastMCP tools that can be easily added"""
    return {
        # Docker-based FastMCP SSE servers
        "webcat": {
            "description": "Web search service (Docker FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "tmfrisinger/webcat:latest"],
            "env": {
                "WEBCAT_URL": "http://localhost:8080"
            },
            "setup_args": [],
            "type": "docker-fastmcp"
        },
        "mcp-server": {
            "description": "Project MCP server (Docker FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "mcp:latest"],
            "env": {},
            "setup_args": [],
            "type": "docker-fastmcp"
        },
        "filesystem-docker": {
            "description": "Dockerized filesystem access (FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "-v", "/tmp:/workspace", "fastmcp/filesystem:latest"],
            "env": {},
            "setup_args": ["<host_directory_to_mount>"],
            "type": "docker-fastmcp"
        },
        "postgres-docker": {
            "description": "Dockerized PostgreSQL access (FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "--network", "host", "fastmcp/postgres:latest"],
            "env": {
                "PGHOST": "localhost",
                "PGPORT": "5432",
                "PGDATABASE": "your-db",
                "PGUSER": "your-user",
                "PGPASSWORD": "your-password"
            },
            "setup_args": [],
            "type": "docker-fastmcp"
        },
        "github-docker": {
            "description": "Dockerized GitHub access (FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "fastmcp/github:latest"],
            "env": {
                "GITHUB_TOKEN": "your-github-token"
            },
            "setup_args": [],
            "type": "docker-fastmcp"
        },
        "search-docker": {
            "description": "Dockerized web search (FastMCP SSE)",
            "command": "docker",
            "args": ["run", "--rm", "-i", "fastmcp/search:latest"],
            "env": {
                "SEARCH_API_KEY": "your-search-api-key"
            },
            "setup_args": [],
            "type": "docker-fastmcp"
        }
    }

def show_popular_tools():
    """Show available popular MCP tools"""
    tools = get_popular_tools()
    
    table = Table(title="Popular MCP Tools")
    table.add_column("Tool Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Required Setup", style="yellow")
    
    for tool_name, tool_info in tools.items():
        setup_info = []
        if tool_info.get("env"):
            env_keys = [k for k in tool_info["env"].keys() if "your-" in tool_info["env"][k]]
            if env_keys:
                setup_info.append(f"Env: {', '.join(env_keys)}")
        
        if tool_info.get("setup_args"):
            setup_info.append(f"Args: {' '.join(tool_info['setup_args'])}")
        
        setup_display = "; ".join(setup_info) if setup_info else "None"
        server_type = tool_info.get("type", "unknown").upper()
        
        table.add_row(
            tool_name,
            server_type,
            tool_info["description"],
            setup_display
        )
    
    console.print(table)
    console.print("\n[blue]Use 'weave tool add <tool-name> --popular' to add a popular tool[/blue]")
    console.print("[blue]Use 'weave tool add --help' for custom tool configuration[/blue]") 