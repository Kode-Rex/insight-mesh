"""
CLI commands for domain-context-tool management.
Updated to use Python-based domain and agent system.
"""

import click
import json
import sys
import os
from typing import Optional

# Add the weave package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

@click.group()
def domain():
    """Domain management commands"""
    pass

@domain.command()
@click.option('--format', type=click.Choice(['json', 'table']), default='table')
def list(format):
    """List all available domains"""
    from domains import list_domains, get_domain
    
    domains = list_domains()
    
    if format == 'json':
        click.echo(json.dumps(domains, indent=2))
    else:
        click.echo("Available domains:")
        for domain_name in domains:
            domain_obj = get_domain(domain_name)
            if domain_obj:
                click.echo(f"  {domain_name}: {domain_obj._description}")

@domain.command()
@click.argument('domain_name')
def show(domain_name):
    """Show detailed information about a domain"""
    from domains import get_domain
    
    domain_obj = get_domain(domain_name)
    if not domain_obj:
        click.echo(f"Domain '{domain_name}' not found")
        return
        
    click.echo(f"Domain: {domain_name}")
    click.echo(f"Description: {domain_obj._description}")
    click.echo(f"Contexts: {', '.join(domain_obj.contexts)}")
    click.echo(f"Tools: {', '.join(domain_obj.tools)}")
    click.echo(f"Schemas: {json.dumps(domain_obj.schemas, indent=2)}")

@click.group()
def context():
    """Context management commands"""
    pass

@context.command()
@click.option('--domain', help='Filter contexts by domain')
@click.option('--format', type=click.Choice(['json', 'table']), default='table')
def list(domain, format):
    """List all available contexts"""
    from domains import list_contexts, get_context
    
    contexts = list_contexts()
    
    if format == 'json':
        click.echo(json.dumps(contexts, indent=2))
    else:
        click.echo(f"Available contexts{' for domain ' + domain if domain else ''}:")
        for context_name in contexts:
            context_obj = get_context(context_name)
            if context_obj:
                # Filter by domain if specified
                if domain and hasattr(context_obj, '_domains') and domain not in context_obj._domains:
                    continue
                click.echo(f"  {context_name}: {context_obj._description}")

@context.command()
@click.argument('context_name')
def show(context_name):
    """Show detailed information about a context"""
    from domains import get_context
    
    context_obj = get_context(context_name)
    if not context_obj:
        click.echo(f"Context '{context_name}' not found")
        return
        
    click.echo(f"Context: {context_name}")
    click.echo(f"Description: {context_obj._description}")
    if hasattr(context_obj, '_domains'):
        click.echo(f"Domains: {', '.join(context_obj._domains)}")
    click.echo(f"Tools: {', '.join(context_obj.tools)}")
    click.echo(f"Sources: {json.dumps(context_obj.sources, indent=2)}")

@context.command('inject')
@click.option('--domain', required=True, help='Domain name')
@click.option('--context', required=True, help='Context name')
@click.option('--user-id', required=True, help='User ID for context injection')
@click.option('--format', type=click.Choice(['json']), default='json')
def inject_context(domain, context, user_id, format):
    """Inject context for domain-aware agent execution"""
    from agents import inject_context
    
    result = inject_context(domain, context, user_id)
    click.echo(json.dumps(result, indent=2))

@click.group()
def agent():
    """Agent management commands"""
    pass

@agent.command()
@click.option('--format', type=click.Choice(['json', 'table']), default='table')
def list(format):
    """List all available agents"""
    from agents import list_agents, get_agent
    
    agents = list_agents()
    
    if format == 'json':
        click.echo(json.dumps(agents, indent=2))
    else:
        click.echo("Available agents:")
        for agent_name in agents:
            agent_cls = get_agent(agent_name)
            if agent_cls:
                click.echo(f"  {agent_name}: {agent_cls._description}")

@agent.command()
@click.argument('agent_name')
def show(agent_name):
    """Show detailed information about an agent"""
    from agents import get_agent, create_agent
    
    agent_cls = get_agent(agent_name)
    if not agent_cls:
        click.echo(f"Agent '{agent_name}' not found")
        return
    
    # Create instance to get properties
    agent_instance = create_agent(agent_name)
    
    click.echo(f"Agent: {agent_name}")
    click.echo(f"Description: {agent_cls._description}")
    click.echo(f"Domain: {agent_cls._domain}")
    click.echo(f"Context: {agent_cls._context}")
    if agent_instance:
        click.echo(f"Goal: {agent_instance.goal}")
        click.echo(f"Tools: {', '.join(agent_instance.tools)}")
        click.echo(f"Execution Config: {json.dumps(agent_instance.execution_config, indent=2)}")

@agent.command()
@click.argument('agent_name')
@click.option('--user-id', required=True, help='User ID for agent execution')
@click.option('--query', required=True, help='Query or input for the agent')
def run(agent_name, user_id, query):
    """Run an agent with given input"""
    import asyncio
    from agents import create_agent
    
    agent_instance = create_agent(agent_name, user_id)
    if not agent_instance:
        click.echo(f"Agent '{agent_name}' not found")
        return
    
    async def execute_agent():
        try:
            result = await agent_instance.execute(query)
            return result
        except Exception as e:
            return f"Error executing agent: {e}"
    
    result = asyncio.run(execute_agent())
    click.echo(f"Agent Result: {result}")

@click.command()
@click.option('--domain', help='Show schema for specific domain')
def schema(domain):
    """Show schema mappings across databases"""
    from domains import list_domains, get_domain
    
    if domain:
        domain_obj = get_domain(domain)
        if not domain_obj:
            click.echo(f"Domain '{domain}' not found")
            return
        schemas = domain_obj.schemas
        click.echo(f"Schema mappings for domain '{domain}':")
        click.echo(json.dumps(schemas, indent=2))
    else:
        click.echo("All domain schemas:")
        for domain_name in list_domains():
            domain_obj = get_domain(domain_name)
            if domain_obj:
                schemas = domain_obj.schemas
                click.echo(f"\n{domain_name}:")
                click.echo(json.dumps(schemas, indent=2))

# Register commands with main CLI
def register_domain_commands(cli):
    """Register domain commands with the main CLI"""
    cli.add_command(domain)
    cli.add_command(context)
    cli.add_command(agent)
    cli.add_command(schema) 