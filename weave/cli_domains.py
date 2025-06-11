"""
CLI commands for domain-context-tool management.
Extends the existing weave CLI with domain-aware functionality.
"""

import click
import json
from typing import Optional
from .domain_loader import get_loader

@click.group()
def domain():
    """Domain management commands"""
    pass

@domain.command()
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='table')
def list(format):
    """List all available domains"""
    loader = get_loader()
    domains = loader.list_domains()
    
    if format == 'json':
        click.echo(json.dumps(domains, indent=2))
    elif format == 'yaml':
        import yaml
        click.echo(yaml.dump(domains))
    else:
        click.echo("Available domains:")
        for domain in domains:
            config = loader.domains[domain]
            click.echo(f"  {domain}: {config.description}")

@domain.command()
@click.argument('domain_name')
def show(domain_name):
    """Show detailed information about a domain"""
    loader = get_loader()
    if domain_name not in loader.domains:
        click.echo(f"Domain '{domain_name}' not found")
        return
        
    config = loader.domains[domain_name]
    click.echo(f"Domain: {config.name}")
    click.echo(f"Description: {config.description}")
    click.echo(f"Contexts: {', '.join(config.contexts)}")
    click.echo(f"Tools: {', '.join(config.tools)}")
    click.echo(f"Schemas: {json.dumps(config.schemas, indent=2)}")

@click.group()
def context():
    """Context management commands"""
    pass

@context.command()
@click.option('--domain', help='Filter contexts by domain')
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='table')
def list(domain, format):
    """List all available contexts"""
    loader = get_loader()
    contexts = loader.list_contexts(domain)
    
    if format == 'json':
        click.echo(json.dumps(contexts, indent=2))
    elif format == 'yaml':
        import yaml
        click.echo(yaml.dump(contexts))
    else:
        click.echo(f"Available contexts{' for domain ' + domain if domain else ''}:")
        for context in contexts:
            if context in loader.contexts:
                config = loader.contexts[context]
                click.echo(f"  {context}: {config.description}")

@context.command()
@click.argument('context_name')
def show(context_name):
    """Show detailed information about a context"""
    loader = get_loader()
    if context_name not in loader.contexts:
        click.echo(f"Context '{context_name}' not found")
        return
        
    config = loader.contexts[context_name]
    click.echo(f"Context: {config.name}")
    click.echo(f"Description: {config.description}")
    click.echo(f"Domains: {', '.join(config.domains)}")
    click.echo(f"Tools: {', '.join(config.tools)}")
    click.echo(f"Sources: {json.dumps(config.sources, indent=2)}")

@context.command('inject')
@click.option('--domain', required=True, help='Domain name')
@click.option('--context', required=True, help='Context name')
@click.option('--user-id', required=True, help='User ID for context injection')
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json')
def inject_context(domain, context, user_id, format):
    """Inject context for domain-aware agent execution"""
    loader = get_loader()
    result = loader.inject_context(domain, context, user_id)
    
    if format == 'json':
        click.echo(json.dumps(result, indent=2))
    else:
        import yaml
        click.echo(yaml.dump(result))

@click.group()
def tool():
    """Tool management commands"""
    pass

@tool.command()
@click.option('--domain', help='Filter tools by domain')
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='table')
def list(domain, format):
    """List all available tools"""
    loader = get_loader()
    tools = loader.list_tools(domain)
    
    if format == 'json':
        click.echo(json.dumps(tools, indent=2))
    elif format == 'yaml':
        import yaml
        click.echo(yaml.dump(tools))
    else:
        click.echo(f"Available tools{' for domain ' + domain if domain else ''}:")
        for tool in tools:
            config = loader.tools[tool]
            click.echo(f"  {tool}: {config.description}")

@tool.command()
@click.argument('tool_name')
def show(tool_name):
    """Show detailed information about a tool"""
    loader = get_loader()
    if tool_name not in loader.tools:
        click.echo(f"Tool '{tool_name}' not found")
        return
        
    config = loader.tools[tool_name]
    click.echo(f"Tool: {config.name}")
    click.echo(f"Type: {config.type}")
    click.echo(f"Description: {config.description}")
    click.echo(f"Auth: {config.auth}")
    click.echo(f"Domains: {', '.join(config.domains)}")
    click.echo(f"Config: {json.dumps(config.config, indent=2)}")

@click.command()
@click.option('--domain', help='Show schema for specific domain')
def schema(domain):
    """Show schema mappings across databases"""
    loader = get_loader()
    
    if domain:
        if domain not in loader.domains:
            click.echo(f"Domain '{domain}' not found")
            return
        schemas = loader.get_domain_schemas(domain)
        click.echo(f"Schema mappings for domain '{domain}':")
        click.echo(json.dumps(schemas, indent=2))
    else:
        click.echo("All domain schemas:")
        for domain_name in loader.domains:
            schemas = loader.get_domain_schemas(domain_name)
            click.echo(f"\n{domain_name}:")
            click.echo(json.dumps(schemas, indent=2))

# Register commands with main CLI
def register_domain_commands(cli):
    """Register domain commands with the main CLI"""
    cli.add_command(domain)
    cli.add_command(context)
    cli.add_command(tool)
    cli.add_command(schema) 