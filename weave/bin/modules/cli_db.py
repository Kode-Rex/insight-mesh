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
@click.argument('database', type=click.Choice(get_managed_databases() + ['all']))
@click.argument('action', default='upgrade')
@click.pass_context
def db_migrate_smart(ctx, database, action):
    """Smart migration command that detects database type and uses the appropriate tool.
    
    This command automatically detects whether the database is SQL, graph, or search
    and routes to the correct migration tool (Alembic, neo4j-migrations, or elasticsearch-evolution).
    """
    from .config import (get_database_type, get_database_migration_tool, 
                        get_all_databases, is_database_managed)
    
    if database == 'all':
        # Route to migrate-all command
        ctx.invoke(db_migrate_all)
        return
    
    # Validate database exists and is managed
    if not is_database_managed(database):
        console.print(f"[red]❌ Database '{database}' is not managed by weave or doesn't exist[/red]")
        ctx.exit(1)
    
    db_type = get_database_type(database)
    migration_tool = get_database_migration_tool(database)
    
    console.print(f"[blue]🔄 Migrating {database} database[/blue]")
    console.print(f"[blue]📋 Type: {db_type}, Tool: {migration_tool}[/blue]")
    
    try:
        if db_type == 'sql':
            # Use Alembic for SQL databases
            from .cli_migrate import migrate_database
            result = migrate_database(database, action)
            
        elif db_type == 'graph':
            # Use neo4j-migrations for graph databases
            from .cli_migrate import migrate_neo4j
            # Map action to neo4j-migrations commands
            neo4j_action = action if action in ['migrate', 'info', 'validate', 'clean'] else 'migrate'
            result = migrate_neo4j(neo4j_action)
            
        elif db_type == 'search':
            # Use elasticsearch-evolution for search databases
            from .cli_migrate import migrate_elasticsearch
            # Map action to elasticsearch commands
            es_action = action if action in ['migrate', 'info'] else 'migrate'
            result = migrate_elasticsearch(es_action)
            
        else:
            console.print(f"[red]❌ Unknown database type: {db_type}[/red]")
            ctx.exit(1)
        
        if result:
            console.print(f"[green]✅ {database} migration completed successfully[/green]")
        else:
            console.print(f"[red]❌ {database} migration failed[/red]")
            ctx.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error migrating {database}: {e}[/red]")
        ctx.exit(1)

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
@click.option('--include-sql', is_flag=True, default=True, help='Include SQL databases (PostgreSQL)')
@click.option('--include-graph', is_flag=True, default=True, help='Include graph databases (Neo4j)')
@click.option('--include-search', is_flag=True, default=True, help='Include search databases (Elasticsearch)')
@click.pass_context
def db_migrate_all(ctx, include_sql, include_graph, include_search):
    """Run migrations for all database systems based on their configured types."""
    console.print("[blue]🔄 Running migrations for all database systems[/blue]")
    
    from .config import (get_sql_databases, get_graph_databases, get_search_databases, 
                        get_database_migration_tool, get_database_type)
    
    success = True
    
    # SQL databases (PostgreSQL with Alembic)
    if include_sql:
        sql_databases = get_sql_databases()
        if sql_databases:
            console.print(f"\n[blue]📊 SQL Databases ({len(sql_databases)})[/blue]")
            from .cli_migrate import migrate_database
            
            for db_name in sql_databases:
                try:
                    migration_tool = get_database_migration_tool(db_name)
                    console.print(f"[blue]🔄 Migrating {db_name} database (using {migration_tool})...[/blue]")
                    result = migrate_database(db_name, 'upgrade')
                    if result:
                        console.print(f"[green]✅ {db_name} migration completed[/green]")
                    else:
                        console.print(f"[red]❌ {db_name} migration failed[/red]")
                        success = False
                except Exception as e:
                    console.print(f"[red]❌ Error migrating {db_name}: {e}[/red]")
                    success = False
    
    # Graph databases (Neo4j)
    if include_graph:
        graph_databases = get_graph_databases()
        if graph_databases:
            console.print(f"\n[blue]🕸️  Graph Databases ({len(graph_databases)})[/blue]")
            from .cli_migrate import migrate_neo4j
            
            for db_name in graph_databases:
                try:
                    migration_tool = get_database_migration_tool(db_name)
                    console.print(f"[blue]🔄 Migrating {db_name} database (using {migration_tool})...[/blue]")
                    result = migrate_neo4j('migrate')
                    if result:
                        console.print(f"[green]✅ {db_name} migration completed[/green]")
                    else:
                        console.print(f"[red]❌ {db_name} migration failed[/red]")
                        success = False
                except Exception as e:
                    console.print(f"[red]❌ Error migrating {db_name}: {e}[/red]")
                    success = False
    
    # Search databases (Elasticsearch)
    if include_search:
        search_databases = get_search_databases()
        if search_databases:
            console.print(f"\n[blue]🔍 Search Databases ({len(search_databases)})[/blue]")
            from .cli_migrate import migrate_elasticsearch
            
            for db_name in search_databases:
                try:
                    migration_tool = get_database_migration_tool(db_name)
                    console.print(f"[blue]🔄 Migrating {db_name} database (using {migration_tool})...[/blue]")
                    result = migrate_elasticsearch('migrate')
                    if result:
                        console.print(f"[green]✅ {db_name} migration completed[/green]")
                    else:
                        console.print(f"[red]❌ {db_name} migration failed[/red]")
                        success = False
                except Exception as e:
                    console.print(f"[red]❌ Error migrating {db_name}: {e}[/red]")
                    success = False
    
    if success:
        console.print("\n[green]🎉 All database migrations completed successfully![/green]")
    else:
        console.print("\n[red]💥 Some migrations failed. Check the logs above.[/red]")
        ctx.exit(1)

@db_group.command('info')
@click.pass_context
def db_info(ctx):
    """Show information about all configured databases including types and migration tools."""
    from .config import (get_databases_config, get_database_type, get_database_migration_tool,
                        get_database_connection_config, is_database_managed)
    from rich.table import Table
    
    console.print("[blue]📊 Database Configuration[/blue]\n")
    
    databases_config = get_databases_config()
    
    if not databases_config:
        console.print("[yellow]⚠️  No databases configured[/yellow]")
        return
    
    # Create table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Database", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Migration Tool", style="yellow")
    table.add_column("Managed", style="magenta")
    table.add_column("Description", style="white")
    
    for db_name, db_config in databases_config.items():
        db_type = get_database_type(db_name) or "unknown"
        migration_tool = get_database_migration_tool(db_name) or "none"
        managed = "✅ Yes" if is_database_managed(db_name) else "❌ No"
        description = db_config.get('description', 'No description')
        
        table.add_row(
            db_name,
            db_type,
            migration_tool,
            managed,
            description
        )
    
    console.print(table)
    
    # Show summary by type
    console.print("\n[blue]📋 Summary by Type[/blue]")
    from .config import get_sql_databases, get_graph_databases, get_search_databases
    
    sql_dbs = get_sql_databases()
    graph_dbs = get_graph_databases()
    search_dbs = get_search_databases()
    
    if sql_dbs:
        console.print(f"[green]📊 SQL Databases ({len(sql_dbs)})[/green]: {', '.join(sql_dbs)}")
    if graph_dbs:
        console.print(f"[green]🕸️  Graph Databases ({len(graph_dbs)})[/green]: {', '.join(graph_dbs)}")
    if search_dbs:
        console.print(f"[green]🔍 Search Databases ({len(search_dbs)})[/green]: {', '.join(search_dbs)}")
    
    console.print(f"\n[blue]💡 Use 'weave db migrate <database>' to run migrations for any database[/blue]")
    console.print(f"[blue]💡 Use 'weave db migrate all' to run migrations for all databases[/blue]") 