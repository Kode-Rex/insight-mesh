#!/usr/bin/env python

import click
from rich.console import Console
from .cli_migrate import (
    migrate_up, migrate_down, migrate_create, 
    migrate_status, migrate_history
)
from .config import get_managed_databases, get_database_choices

console = Console()

@click.group('db')
def db_group():
    """Database management commands"""
    pass

# Wrap the migration commands with more intuitive names
@db_group.command('migrate')
@click.option('--database', '-d', type=click.Choice(get_database_choices()), 
              default='all', help='Database to migrate')
@click.option('--skip-db-creation', is_flag=True, help='Skip database creation step')
@click.pass_context
def db_migrate(ctx, database, skip_db_creation):
    """Run database migrations (upgrade to latest)
    
    This command will:
    1. Create databases if they don't exist (unless --skip-db-creation is used)
    2. Run table creation and data migrations
    
    Examples:
    
    Migrate all databases:
    weave db migrate
    
    Migrate specific database:
    weave db migrate --database slack
    
    Skip database creation (if databases already exist):
    weave db migrate --skip-db-creation
    """
    # Call the underlying migrate_up function
    ctx.invoke(migrate_up, database=database, skip_db_creation=skip_db_creation)

@db_group.command('rollback')
@click.option('--database', '-d', type=click.Choice(get_managed_databases()), 
              required=True, help='Database to rollback')
@click.option('--revision', '-r', help='Target revision to rollback to')
@click.pass_context
def db_rollback(ctx, database, revision):
    """Rollback database migrations
    
    Examples:
    
    Rollback one migration:
    weave db rollback --database slack
    
    Rollback to specific revision:
    weave db rollback --database slack --revision 001
    """
    # Call the underlying migrate_down function
    ctx.invoke(migrate_down, database=database, revision=revision)

@db_group.command('create')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.argument('message')
@click.option('--auto', '-a', is_flag=True, help='Auto-detect model changes and generate migration')
@click.pass_context
def db_create_migration(ctx, database, message, auto):
    """Create a new migration file (Auto detects model changes)
    
    This command can automatically detect changes in your domain models
    and generate the appropriate migration code.
    
    Examples:
    
    Create a new Slack migration:
    weave db create slack "add user preferences table"
    
    Auto-generate migration based on model changes:
    weave db create slack "auto detected changes" --auto
    
    Create a new InsightMesh migration:
    weave db create insightmesh "add message threading"
    """
    if auto:
        console.print(f"[blue]🔍 Auto-detecting model changes for {database} database...[/blue]")
        
        # Use alembic's autogenerate feature
        from .cli_migrate import create_migration_autogenerate
        try:
            ctx.invoke(create_migration_autogenerate, database=database, message=message)
        except AttributeError:
            # Fallback to regular creation if autogenerate function doesn't exist
            console.print("[yellow]⚠️  Auto-detection not available, creating empty migration...[/yellow]")
            ctx.invoke(migrate_create, database=database, message=message)
    else:
        # Call the underlying migrate_create function
        ctx.invoke(migrate_create, database=database, message=message)

@db_group.command('status')
@click.option('--database', '-d', type=click.Choice(get_database_choices()), 
              default='all', help='Database to check')
@click.pass_context
def db_status(ctx, database):
    """Show current migration status
    
    Examples:
    
    Check all databases:
    weave db status
    
    Check specific database:
    weave db status --database slack
    """
    # Call the underlying migrate_status function
    ctx.invoke(migrate_status, database=database)

@db_group.command('history')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.pass_context
def db_history(ctx, database):
    """Show migration history for a database
    
    Examples:
    
    Show Slack migration history:
    weave db history slack
    
    Show InsightMesh migration history:
    weave db history insightmesh
    """
    # Call the underlying migrate_history function
    ctx.invoke(migrate_history, database=database)

# Additional database utility commands
@db_group.command('reset')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def db_reset(ctx, database, force):
    """Reset a database (rollback all migrations and re-run them)
    
    WARNING: This will destroy all data in the specified database!
    
    Examples:
    
    Reset Slack database:
    weave db reset slack
    
    Reset without confirmation:
    weave db reset slack --force
    """
    if not force:
        if not click.confirm(f'This will destroy all data in the {database} database. Continue?'):
            console.print("[yellow]Operation cancelled[/yellow]")
            return
    
    console.print(f"[red]Resetting {database} database...[/red]")
    
    # First rollback all migrations
    try:
        ctx.invoke(migrate_down, database=database, revision='base')
        console.print(f"[green]✅ Rolled back all migrations for {database}[/green]")
    except Exception as e:
        console.print(f"[yellow]Warning during rollback: {e}[/yellow]")
    
    # Then re-run all migrations
    ctx.invoke(migrate_up, database=database, skip_db_creation=True)
    console.print(f"[green]🎉 Database {database} has been reset successfully![/green]")

@db_group.command('seed')
@click.option('--database', '-d', type=click.Choice(get_database_choices()), 
              default='all', help='Database to seed')
@click.pass_context
def db_seed(ctx, database):
    """Seed databases with sample data
    
    Examples:
    
    Seed all databases:
    weave db seed
    
    Seed specific database:
    weave db seed --database slack
    """
    console.print(f"[blue]Seeding {database} database(s)...[/blue]")
    
    if database in ['slack', 'all']:
        # Load sample Slack data
        sample_data_file = ".weave/migrations/sample-slack-data.sql"
        try:
            import subprocess
            import os
            
            env = os.environ.copy()
            env.setdefault('POSTGRES_USER', 'postgres')
            env.setdefault('POSTGRES_PASSWORD', 'postgres')
            env.setdefault('POSTGRES_HOST', 'localhost')
            env.setdefault('POSTGRES_PORT', '5432')
            
            cmd = [
                'psql',
                f"postgresql://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@{env['POSTGRES_HOST']}:{env['POSTGRES_PORT']}/slack",
                '-f', sample_data_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✅ Seeded slack database with sample Slack data[/green]")
            else:
                console.print(f"[yellow]Warning: Could not seed slack database: {result.stderr}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not seed slack database: {e}[/yellow]")
    
    if database in ['insightmesh', 'all']:
        console.print("[blue]ℹ️  InsightMesh database seeding not yet implemented[/blue]")
    
    console.print("[green]🌱 Database seeding completed![/green]") 