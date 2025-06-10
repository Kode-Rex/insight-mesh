#!/usr/bin/env python

import os
import sys
import subprocess
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .config import get_managed_databases, get_all_databases, get_database_choices

console = Console()

def get_env():
    """Get environment variables for database connections"""
    env = os.environ.copy()
    
    # Set default values if not provided
    env.setdefault('POSTGRES_USER', 'postgres')
    env.setdefault('POSTGRES_PASSWORD', 'postgres')
    env.setdefault('POSTGRES_HOST', 'localhost')
    env.setdefault('POSTGRES_PORT', '5432')
    
    return env

def run_command(cmd, cwd=None, env=None):
    """Run a shell command and return the result"""
    console.print(f"[blue]Running:[/blue] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Error:[/red] {result.stderr}")
        sys.exit(1)
    return result.stdout

def get_project_root():
    """Get the project root directory"""
    return Path.cwd()

def get_migrations_dir():
    """Get the migrations directory"""
    return get_project_root() / '.weave' / 'migrations'

def create_databases():
    """Create the required databases if they don't exist"""
    env = get_env()
    
    # Connect to the default postgres database
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    try:
        # Connection parameters
        conn_params = {
            'host': env.get('POSTGRES_HOST', 'localhost'),
            'port': env.get('POSTGRES_PORT', '5432'),
            'user': env.get('POSTGRES_USER', 'postgres'),
            'password': env.get('POSTGRES_PASSWORD', 'postgres'),
            'database': 'postgres'  # Connect to default database
        }
        
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # List of databases to create
        databases = get_all_databases()
        
        for db_name in databases:
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            
            if not cursor.fetchone():
                # Database doesn't exist, create it
                cursor.execute(f'CREATE DATABASE "{db_name}"')
                console.print(f"[green]✅ Created database: {db_name}[/green]")
            else:
                console.print(f"[blue]ℹ️  Database already exists: {db_name}[/blue]")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Error creating databases: {e}[/red]")
        console.print("[yellow]💡 Make sure PostgreSQL is running and accessible[/yellow]")
        return False

def migrate_database(schema_name, action='upgrade'):
    """Run migration for a specific schema using schema-specific directories"""
    env = get_env()
    project_root = get_project_root()
    
    # Use schema-specific migration directory
    schema_migrations_dir = project_root / '.weave' / 'migrations' / schema_name
    
    if not schema_migrations_dir.exists():
        console.print(f"[red]❌ Migration directory for schema '{schema_name}' does not exist[/red]")
        return False
    
    cmd = [
        'python', '-m', 'alembic',
        '-c', str(schema_migrations_dir / 'alembic.ini'),
        action
    ]
    
    if action == 'upgrade':
        cmd.append('head')
    
    return run_command(cmd, cwd=str(project_root), env=env)

def migrate_all(action='upgrade'):
    """Run migrations for all schemas"""
    schemas = get_managed_databases()
    
    for schema in schemas:
        console.print(f"\n{'='*50}")
        console.print(f"[bold blue]Running {action} for {schema} schema[/bold blue]")
        console.print(f"{'='*50}")
        migrate_database(schema, action)
        console.print(f"[green]✅ {action.capitalize()} completed for {schema}[/green]")

def create_migration(schema_name, message):
    """Create a new migration for a specific schema"""
    env = get_env()
    project_root = get_project_root()
    
    # Use schema-specific migration directory
    schema_migrations_dir = project_root / '.weave' / 'migrations' / schema_name
    
    if not schema_migrations_dir.exists():
        console.print(f"[red]❌ Migration directory for schema '{schema_name}' does not exist[/red]")
        return False
    
    cmd = [
        'python', '-m', 'alembic',
        '-c', str(schema_migrations_dir / 'alembic.ini'),
        'revision',
        '-m', message
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def create_migration_autogenerate(schema_name, message):
    """Create a new migration with autogenerate for a specific schema"""
    env = get_env()
    project_root = get_project_root()
    
    # Use schema-specific migration directory
    schema_migrations_dir = project_root / '.weave' / 'migrations' / schema_name
    
    if not schema_migrations_dir.exists():
        console.print(f"[red]❌ Migration directory for schema '{schema_name}' does not exist[/red]")
        return False
    
    cmd = [
        'python', '-m', 'alembic',
        '-c', str(schema_migrations_dir / 'alembic.ini'),
        'revision',
        '--autogenerate',
        '-m', message
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def show_current_revision(schema_name):
    """Show current revision for a schema"""
    env = get_env()
    project_root = get_project_root()
    
    # Use schema-specific migration directory
    schema_migrations_dir = project_root / '.weave' / 'migrations' / schema_name
    
    if not schema_migrations_dir.exists():
        console.print(f"[red]❌ Migration directory for schema '{schema_name}' does not exist[/red]")
        return ""
    
    cmd = [
        'python', '-m', 'alembic',
        '-c', str(schema_migrations_dir / 'alembic.ini'),
        'current'
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def show_migration_history(schema_name):
    """Show migration history for a schema"""
    env = get_env()
    project_root = get_project_root()
    
    # Use schema-specific migration directory
    schema_migrations_dir = project_root / '.weave' / 'migrations' / schema_name
    
    if not schema_migrations_dir.exists():
        console.print(f"[red]❌ Migration directory for schema '{schema_name}' does not exist[/red]")
        return ""
    
    cmd = [
        'python', '-m', 'alembic',
        '-c', str(schema_migrations_dir / 'alembic.ini'),
        'history'
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

@click.group('migrate', invoke_without_command=True)
@click.pass_context
def migrate_group(ctx):
    """Manage database migrations using Alembic"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@migrate_group.command('up')
@click.option('--database', '-d', type=click.Choice(get_database_choices()), 
              default='all', help='Database to migrate')
@click.option('--skip-db-creation', is_flag=True, help='Skip database creation step')
@click.pass_context
def migrate_up(ctx, database, skip_db_creation):
    """Run database migrations (upgrade to latest)
    
    This command will:
    1. Create databases if they don't exist (unless --skip-db-creation is used)
    2. Run table creation and data migrations
    
    Examples:
    
    Migrate all databases:
    weave migrate up
    
    Migrate specific database:
    weave migrate up --database mcp
    
    Skip database creation (if databases already exist):
    weave migrate up --skip-db-creation
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    if verbose:
        console.print(f"[blue]Running migrations for: {database}[/blue]")
    
    try:
        # Step 1: Create databases if needed
        if not skip_db_creation:
            console.print("[bold blue]🗄️  Creating databases...[/bold blue]")
            if not create_databases():
                console.print("[red]❌ Failed to create databases. Aborting migration.[/red]")
                sys.exit(1)
            console.print("[green]✅ Database creation completed[/green]\n")
        else:
            console.print("[yellow]⏭️  Skipping database creation[/yellow]\n")
        
        # Step 2: Run table migrations
        console.print("[bold blue]📋 Running table migrations...[/bold blue]")
        if database == 'all':
            migrate_all('upgrade')
        else:
            console.print(f"[bold blue]Running upgrade for {database} schema[/bold blue]")
            migrate_database(database, 'upgrade')
            console.print(f"[green]✅ Upgrade completed for {database}[/green]")
            
        console.print("\n[green]🎉 All migrations completed successfully![/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@migrate_group.command('down')
@click.option('--database', '-d', type=click.Choice(get_managed_databases()), 
              required=True, help='Database to rollback')
@click.option('--revision', '-r', help='Target revision to rollback to')
@click.pass_context
def migrate_down(ctx, database, revision):
    """Rollback database migrations
    
    Examples:
    
    Rollback one migration:
    weave migrate down --database mcp
    
    Rollback to specific revision:
    weave migrate down --database mcp --revision abc123
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    if verbose:
        console.print(f"[blue]Rolling back migrations for: {database}[/blue]")
    
    try:
        action = 'downgrade'
        if revision:
            action = f'downgrade {revision}'
        else:
            action = 'downgrade -1'  # Rollback one migration
            
        console.print(f"[bold yellow]Running rollback for {database} schema[/bold yellow]")
        migrate_database(database, action)
        console.print(f"[green]✅ Rollback completed for {database}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@migrate_group.command('create')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.argument('message')
@click.option('--autogenerate', '-a', is_flag=True, help='Auto-detect model changes')
@click.pass_context
def migrate_create(ctx, database, message, autogenerate):
    """Create a new migration
    
    Examples:
    
    Create MCP migration:
    weave migrate create mcp "add user preferences table"
    
    Auto-generate migration based on model changes:
    weave migrate create mcp "auto detected changes" --autogenerate
    
    Create Slack migration:
    weave migrate create insight_mesh "add slack message history"
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    if verbose:
        console.print(f"[blue]Creating migration for {database}: {message}[/blue]")
    
    try:
        if autogenerate:
            console.print(f"[bold blue]Creating auto-generated migration for {database} schema[/bold blue]")
            result = create_migration_autogenerate(database, message)
        else:
            console.print(f"[bold blue]Creating new migration for {database} schema[/bold blue]")
            result = create_migration(database, message)
            
        console.print(f"[green]✅ Migration created successfully[/green]")
        
        if verbose and result:
            console.print(f"[blue]Output:[/blue] {result}")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@migrate_group.command('status')
@click.option('--database', '-d', type=click.Choice(get_database_choices()), 
              default='all', help='Database to check')
@click.pass_context
def migrate_status(ctx, database):
    """Show migration status
    
    Examples:
    
    Show status for all databases:
    weave migrate status
    
    Show status for specific database:
    weave migrate status --database mcp
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    try:
        if database == 'all':
            table = Table(title="Database Migration Status")
            table.add_column("Database", style="cyan", no_wrap=True)
            table.add_column("Current Revision", style="green")
            
            for db in get_managed_databases():
                try:
                    revision = show_current_revision(db).strip()
                    if not revision:
                        revision = "[yellow]No migrations applied[/yellow]"
                    table.add_row(db, revision)
                except Exception as e:
                    table.add_row(db, f"[red]Error: {str(e)}[/red]")
            
            console.print(table)
        else:
            console.print(f"[bold blue]{database} schema status:[/bold blue]")
            revision = show_current_revision(database)
            if revision.strip():
                console.print(f"[green]Current revision: {revision.strip()}[/green]")
            else:
                console.print("[yellow]No migrations applied[/yellow]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@migrate_group.command('history')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.pass_context
def migrate_history(ctx, database):
    """Show migration history
    
    Examples:
    
    Show MCP migration history:
    weave migrate history mcp
    
    Show Slack migration history:
    weave migrate history insight_mesh
    """
    verbose = ctx.obj.get('VERBOSE', False)
    
    try:
        console.print(f"[bold blue]{database} migration history:[/bold blue]")
        history = show_migration_history(database)
        console.print(history)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1) 