#!/usr/bin/env python

import click
from rich.console import Console
from .cli_migrate import (
    migrate_up, migrate_down, migrate_create, 
    migrate_status, migrate_history
)
from .config import get_managed_databases, get_database_choices

console = Console()

@click.group('db', invoke_without_command=True)
@click.pass_context
def db_group(ctx):
    """Database management commands"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Wrap the migration commands with more intuitive names
@db_group.command('migrate')
@click.argument('database', type=click.Choice(get_database_choices()), required=False)
@click.option('--skip-db-creation', is_flag=True, help='Skip database creation step')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without running it')
@click.pass_context
def db_migrate(ctx, database, skip_db_creation, dry_run):
    """Run database migrations (upgrade to latest)
    
    This command will:
    1. Create databases if they don't exist (unless --skip-db-creation is used)
    2. Run table creation and data migrations
    
    Examples:
    
    Migrate all databases:
    weave db migrate
    weave db migrate all
    
    Migrate specific database:
    weave db migrate slack
    weave db migrate insightmesh
    
    Preview what would be migrated:
    weave db migrate --dry-run
    weave db migrate slack --dry-run
    
    Skip database creation (if databases already exist):
    weave db migrate --skip-db-creation
    """
    # Default to 'all' if no database specified
    if database is None:
        database = 'all'
    if dry_run:
        console.print("[bold blue]🔍 DRY RUN - Showing what would be executed:[/bold blue]")
        console.print()
        
        if not skip_db_creation:
            console.print("[blue]📋 Would create databases:[/blue]")
            from .config import get_all_databases
            for db_name in get_all_databases():
                console.print(f"  • {db_name}")
            console.print()
        
        console.print("[blue]📋 Would run migrations for:[/blue]")
        if database == 'all':
            from .config import get_managed_databases
            for db_name in get_managed_databases():
                console.print(f"  • {db_name} database → {db_name}@head")
        else:
            console.print(f"  • {database} database → {database}@head")
        
        console.print()
        console.print("[yellow]💡 Run without --dry-run to execute these operations[/yellow]")
        return
    
    # Call the underlying migrate_up function
    ctx.invoke(migrate_up, database=database, skip_db_creation=skip_db_creation)

@db_group.command('rollback')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.option('--revision', '-r', help='Target revision to rollback to')
@click.option('--dry-run', is_flag=True, help='Show what would be rolled back without doing it')
@click.pass_context
def db_rollback(ctx, database, revision, dry_run):
    """Rollback database migrations
    
    Examples:
    
    Rollback one migration:
    weave db rollback slack
    
    Rollback to specific revision:
    weave db rollback slack --revision 001
    
    Preview what would be rolled back:
    weave db rollback slack --dry-run
    """
    if dry_run:
        console.print("[bold blue]🔍 DRY RUN - Showing what would be rolled back:[/bold blue]")
        console.print()
        
        console.print(f"[blue]📋 Would rollback {database} database:[/blue]")
        if revision:
            console.print(f"  • Target revision: {revision}")
            console.print(f"  • Action: Rollback to specific revision")
        else:
            console.print(f"  • Target: Previous migration")
            console.print(f"  • Action: Rollback one migration")
        
        console.print()
        console.print("[yellow]💡 Run without --dry-run to execute the rollback[/yellow]")
        return
    
    # Call the underlying migrate_down function
    ctx.invoke(migrate_down, database=database, revision=revision)

@db_group.command('create')
@click.argument('database', type=click.Choice(get_managed_databases()))
@click.argument('message')
@click.option('--auto', '-a', is_flag=True, help='Auto-detect model changes and generate migration')
@click.option('--dry-run', is_flag=True, help='Show what migration would be created without creating it')
@click.pass_context
def db_create_migration(ctx, database, message, auto, dry_run):
    """Create a new migration file (Auto detects model changes)
    
    This command can automatically detect changes in your domain models
    and generate the appropriate migration code.
    
    Examples:
    
    Create a new Slack migration:
    weave db create slack "add user preferences table"
    
    Auto-generate migration based on model changes:
    weave db create slack "auto detected changes" --auto
    
    Preview what migration would be created:
    weave db create slack "test migration" --dry-run
    
    Create a new InsightMesh migration:
    weave db create insightmesh "add message threading"
    """
    if dry_run:
        console.print("[bold blue]🔍 DRY RUN - Showing what would be created:[/bold blue]")
        console.print()
        
        # Generate the migration filename that would be created
        import time
        timestamp = int(time.time())
        revision_id = f"{database}_{timestamp % 1000:03d}"
        filename = f"{database}_{revision_id}_{message.lower().replace(' ', '_')}.py"
        
        console.print(f"[blue]📄 Would create migration file:[/blue]")
        console.print(f"  • File: .weave/migrations/versions/{filename}")
        console.print(f"  • Revision ID: {revision_id}")
        console.print(f"  • Branch: {database}")
        console.print(f"  • Message: {message}")
        
        if auto:
            console.print(f"  • Type: Auto-generated (detects model changes)")
        else:
            console.print(f"  • Type: Empty template")
        
        console.print()
        console.print("[yellow]💡 Run without --dry-run to create the migration file[/yellow]")
        return
    
    if auto:
        console.print(f"[blue]🔍 Auto-detecting model changes for {database} database...[/blue]")
        
        # Use alembic's autogenerate feature
        from .cli_migrate import create_migration_autogenerate
        try:
            result = create_migration_autogenerate(database, message)
            console.print(f"[green]✅ Auto-generated migration created successfully[/green]")
        except Exception as e:
            # Fallback to regular creation if autogenerate function doesn't work
            console.print(f"[yellow]⚠️  Auto-detection failed ({e}), creating empty migration...[/yellow]")
            from .cli_migrate import create_migration
            result = create_migration(database, message)
            console.print(f"[green]✅ Empty migration created successfully[/green]")
    else:
        # Call the underlying create_migration function directly
        from .cli_migrate import create_migration
        result = create_migration(database, message)
        console.print(f"[green]✅ Migration created successfully[/green]")

@db_group.command('status')
@click.argument('database', type=click.Choice(get_database_choices()), required=False)
@click.pass_context
def db_status(ctx, database):
    """Show current migration status
    
    Examples:
    
    Check all databases:
    weave db status
    weave db status all
    
    Check specific database:
    weave db status slack
    weave db status insightmesh
    """
    # Default to 'all' if no database specified
    if database is None:
        database = 'all'
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

@db_group.command('migrate-neo4j')
@click.argument('action', type=click.Choice(['info', 'migrate', 'validate', 'clean']), default='migrate')
@click.pass_context
def db_migrate_neo4j(ctx, action):
    """Run Neo4j migrations using neo4j-migrations tool.
    
    Actions:
    - info: Show migration information
    - migrate: Apply pending migrations
    - validate: Validate migration files
    - clean: Clean the database (removes all data)
    """
    console.print(f"[blue]🔄 Neo4j Migration: {action}[/blue]")
    
    from .cli_migrate import migrate_neo4j
    
    try:
        result = migrate_neo4j(action)
        if result:
            console.print(f"[green]✅ Neo4j migration '{action}' completed successfully[/green]")
        else:
            console.print(f"[red]❌ Neo4j migration '{action}' failed[/red]")
            ctx.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error running Neo4j migration: {e}[/red]")
        ctx.exit(1)

@db_group.command('migrate-elasticsearch')
@click.argument('action', type=click.Choice(['info', 'migrate']), default='migrate')
@click.pass_context
def db_migrate_elasticsearch(ctx, action):
    """Run Elasticsearch migrations using HTTP-based migration files.
    
    Actions:
    - info: Show current indices and templates
    - migrate: Apply pending index migrations
    """
    console.print(f"[blue]🔄 Elasticsearch Migration: {action}[/blue]")
    
    from .cli_migrate import migrate_elasticsearch
    
    try:
        result = migrate_elasticsearch(action)
        if result:
            console.print(f"[green]✅ Elasticsearch migration '{action}' completed successfully[/green]")
        else:
            console.print(f"[red]❌ Elasticsearch migration '{action}' failed[/red]")
            ctx.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error running Elasticsearch migration: {e}[/red]")
        ctx.exit(1)

@db_group.command('migrate-all')
@click.option('--include-postgres', is_flag=True, default=True, help='Include PostgreSQL migrations')
@click.option('--include-neo4j', is_flag=True, default=True, help='Include Neo4j migrations')
@click.option('--include-elasticsearch', is_flag=True, default=True, help='Include Elasticsearch migrations')
@click.pass_context
def db_migrate_all(ctx, include_postgres, include_neo4j, include_elasticsearch):
    """Run migrations for all database systems."""
    console.print("[blue]🔄 Running migrations for all database systems[/blue]")
    
    success = True
    
    # PostgreSQL migrations
    if include_postgres:
        console.print("\n[blue]📊 PostgreSQL Migrations[/blue]")
        from .cli_migrate import migrate_database
        
        for db_name in get_managed_databases():
            try:
                console.print(f"[blue]🔄 Migrating {db_name} database...[/blue]")
                result = migrate_database(db_name, 'upgrade')
                if result:
                    console.print(f"[green]✅ {db_name} migration completed[/green]")
                else:
                    console.print(f"[red]❌ {db_name} migration failed[/red]")
                    success = False
            except Exception as e:
                console.print(f"[red]❌ Error migrating {db_name}: {e}[/red]")
                success = False
    
    # Neo4j migrations
    if include_neo4j:
        console.print("\n[blue]🕸️  Neo4j Migrations[/blue]")
        try:
            from .cli_migrate import migrate_neo4j
            result = migrate_neo4j('migrate')
            if result:
                console.print("[green]✅ Neo4j migration completed[/green]")
            else:
                console.print("[red]❌ Neo4j migration failed[/red]")
                success = False
        except Exception as e:
            console.print(f"[red]❌ Error migrating Neo4j: {e}[/red]")
            success = False
    
    # Elasticsearch migrations
    if include_elasticsearch:
        console.print("\n[blue]🔍 Elasticsearch Migrations[/blue]")
        try:
            from .cli_migrate import migrate_elasticsearch
            result = migrate_elasticsearch('migrate')
            if result:
                console.print("[green]✅ Elasticsearch migration completed[/green]")
            else:
                console.print("[red]❌ Elasticsearch migration failed[/red]")
                success = False
        except Exception as e:
            console.print(f"[red]❌ Error migrating Elasticsearch: {e}[/red]")
            success = False
    
    if success:
        console.print("\n[green]🎉 All database migrations completed successfully![/green]")
    else:
        console.print("\n[red]💥 Some migrations failed. Check the logs above.[/red]")
        ctx.exit(1) 