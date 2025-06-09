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
        console.print("[yellow]Please create the configuration file or use 'weave tool config --path' to set a different path[/yellow]")
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

def list_tools(verbose=False):
    """List all trusted MCP tools from configuration"""
    config = load_mcp_config()
    servers = config.get("mcpServers", {})
    
    if not servers:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print(f"[yellow]Configuration file location: {get_mcp_config_path()}[/yellow]")
        return
    
    table = Table(title="Trusted MCP Tools")
    table.add_column("Tool Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="blue", no_wrap=True)
    table.add_column("Image/Endpoint", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Version", style="magenta")
    table.add_column("Environment Variables", style="blue")
    table.add_column("Description", style="dim")
    
    for server_name, server_config in servers.items():
        server_type = server_config.get("type", "docker")  # Default to docker for backward compatibility
        command = server_config.get("command", "N/A")
        args = server_config.get("args", [])
        env_vars = server_config.get("env", {})
        
        # Handle different server types
        if server_type == "cloud":
            # Cloud-hosted MCP server
            endpoint = server_config.get("endpoint", "N/A")
            image_or_endpoint = endpoint
            status = check_cloud_tool_availability(endpoint)
            version = server_config.get("version", "N/A")
            
        else:
            # Docker-based MCP server (default)
            # Build full command string
            full_command = f"{command} {' '.join(args)}" if args else command
            
            # Check if tool is available
            status = check_tool_availability(command, args)
            
            # Extract docker image and version from command
            docker_image = "N/A"
            version = "latest"
            
            if command == "docker" and args:
                # Build full command to parse
                full_command_parts = [command] + args
                full_command_str = " ".join(full_command_parts)
                
                if "run" in full_command_parts:
                    # Find the image name in the args (usually the last argument that contains a colon or looks like an image)
                    for part in reversed(args):  # Start from the end as image is usually last
                        # Skip flags and options
                        if part.startswith("-") or "=" in part:
                            continue
                        # Look for image patterns (contains / or :, doesn't start with -)
                        if ("/" in part or ":" in part) and not part.startswith("-"):
                            docker_image = part
                            if ":" in docker_image:
                                image_parts = docker_image.split(":")
                                docker_image = image_parts[0]
                                version = image_parts[1]
                            break
                        # Also check for simple image names without / or :
                        elif part and not part.startswith("-") and part not in ["run", "--rm", "-i", "-v", "--network", "host"]:
                            # This might be a simple image name like "mcp:latest"
                            if ":" in part:
                                image_parts = part.split(":")
                                docker_image = image_parts[0]
                                version = image_parts[1]
                            else:
                                docker_image = part
                            break
            
            image_or_endpoint = docker_image
        
        # Format environment variables for display (show only required var names)
        env_vars_display = []
        if env_vars:
            for key, value in env_vars.items():
                # Mark as required if value is empty, starts with "your-", or contains placeholder text
                is_required = (not value or 
                             str(value).startswith("your-") or 
                             "your-" in str(value).lower() or
                             str(value) in ["", "placeholder", "required"])
                
                if is_required:
                    env_vars_display.append(f"{key}*")
                else:
                    env_vars_display.append(key)
        
        env_display = ", ".join(env_vars_display) if env_vars_display else "None"
        
        table.add_row(
            server_name,
            server_type.title(),
            image_or_endpoint,
            status,
            version,
            env_display,
            server_config.get("description", "N/A")
        )
    
    console.print(table)
    console.print(f"\n[blue]Configuration file: {get_mcp_config_path()}[/blue]")
    console.print("[dim]* indicates required environment variables[/dim]")

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

def check_cloud_tool_availability(endpoint):
    """Check if a cloud-hosted MCP server is available"""
    # For cloud-hosted MCP servers, we can't reliably check availability
    # without proper authentication and MCP protocol handshake
    # So we'll just return a neutral status
    return "[blue]Cloud Service[/blue]"

def add_tool(server_name, command=None, args=None, env=None, server_type="docker", endpoint=None, version=None, description=None, force=False):
    """Add a new MCP tool to the configuration"""
    config = load_mcp_config()
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Check if server already exists
    if server_name in config["mcpServers"] and not force:
        console.print(f"[yellow]Server '{server_name}' already exists. Use --force to overwrite.[/yellow]")
        return False
    
    # Build server configuration based on type
    if server_type == "cloud":
        if not endpoint:
            console.print("[red]Cloud-hosted servers require an endpoint URL[/red]")
            return False
            
        server_config = {
            "type": "cloud",
            "endpoint": endpoint,
            "env": env or {},
            "version": version or "N/A",
            "description": description or "Cloud-hosted MCP server"
        }
        
        # Show the added configuration
        panel_content = f"""
[cyan]Server Name:[/cyan] {server_name}
[cyan]Type:[/cyan] Cloud-hosted
[cyan]Endpoint:[/cyan] {endpoint}
[cyan]Version:[/cyan] {version or 'N/A'}
[cyan]Environment Variables:[/cyan] {len(env or {})} configured
        """
        
    else:
        # Docker-based server (default)
        if not command:
            console.print("[red]Docker-based servers require a command[/red]")
            return False
            
        server_config = {
            "type": "docker",
            "command": command,
            "args": args or [],
            "env": env or {},
            "description": description or "Docker-based MCP server"
        }
        
        # Show the added configuration
        panel_content = f"""
[cyan]Server Name:[/cyan] {server_name}
[cyan]Type:[/cyan] Docker-based
[cyan]Command:[/cyan] {command}
[cyan]Arguments:[/cyan] {' '.join(args) if args else 'None'}
[cyan]Environment Variables:[/cyan] {len(env or {})} configured
        """
    
    config["mcpServers"][server_name] = server_config
    
    if save_mcp_config(config):
        console.print(f"[green]Successfully added MCP server '{server_name}'[/green]")
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
    server_type = server_config.get("type", "docker")
    env_vars = server_config.get("env", {})
    
    console.print(f"[blue]Installing/testing MCP server: {server_name}[/blue]")
    
    if server_type == "cloud":
        # Cloud-hosted MCP server
        endpoint = server_config.get("endpoint")
        
        if verbose:
            console.print(f"[blue]Type: Cloud-hosted[/blue]")
            console.print(f"[blue]Endpoint: {endpoint}[/blue]")
            console.print(f"[blue]Environment variables: {list(env_vars.keys())}[/blue]")
        
        # For cloud-hosted services, we can't really "install" or test them
        # We can only verify the configuration is complete
        console.print(f"[blue]Cloud MCP server '{server_name}' configuration:[/blue]")
        console.print(f"[green]✓ Endpoint configured: {endpoint}[/green]")
        
        # Check if required environment variables are set
        missing_vars = []
        for key, value in env_vars.items():
            if not value or str(value).startswith("your-") or "your-" in str(value).lower():
                missing_vars.append(key)
        
        if missing_vars:
            console.print(f"[yellow]⚠ Environment variables need configuration: {', '.join(missing_vars)}[/yellow]")
            console.print("[yellow]Please set these variables in your environment or configuration file[/yellow]")
        else:
            console.print("[green]✓ All environment variables appear to be configured[/green]")
        
        console.print(f"[blue]Note: Cloud services require proper authentication and cannot be tested locally[/blue]")
        return True
    
    else:
        # Docker-based MCP server
        command = server_config.get("command")
        args = server_config.get("args", [])
        
        # Prepare environment
        env = os.environ.copy()
        env.update(env_vars)
        
        # Build command
        full_command = [command] + args
        
        if verbose:
            console.print(f"[blue]Type: Docker-based[/blue]")
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

 