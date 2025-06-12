#!/usr/bin/env python

import click
from rich.console import Console

from .config import get_managed_databases, get_database_choices
from .cli_db_tools import db_tool_group

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
@click.option('--dry-run', is_flag=True, help='Show what migrations would be run without executing them')
@click.pass_context
def db_migrate_smart(ctx, database, action, dry_run):
    """Smart migration command that detects database type and uses the appropriate tool.
    
    This command automatically detects whether the database is SQL, graph, or search
    and routes to the correct migration tool (Alembic, neo4j-migrations, or elasticsearch-evolution).
    """
    from .config import (get_database_type, get_database_migration_tool, 
                        get_all_databases, is_database_managed)
    
    if dry_run:
        console.print("[bold blue]🔍 DRY RUN - Showing what migrations would be executed:[/bold blue]")
        console.print()
    
    if database == 'all':
        # Migrate all databases
        if dry_run:
            console.print("[blue]📋 Would migrate all database systems:[/blue]")
        else:
            console.print("[blue]🔄 Running migrations for all database systems[/blue]")
        
        from .config import (get_sql_databases, get_graph_databases, get_search_databases, 
                            get_database_migration_tool, get_database_type)
        
        success = True
        all_databases = get_managed_databases()
        
        for db_name in all_databases:
            try:
                db_type = get_database_type(db_name)
                migration_tool = get_database_migration_tool(db_name)
                
                if dry_run:
                    console.print(f"[blue]📋 Would migrate {db_name} database:[/blue]")
                    console.print(f"  • Type: {db_type}")
                    console.print(f"  • Tool: {migration_tool}")
                    console.print(f"  • Action: {action}")
                    continue
                
                console.print(f"[blue]🔄 Migrating {db_name} database (using {migration_tool})...[/blue]")
                
                if db_type == 'sql':
                    from .cli_migrate import migrate_database
                    result = migrate_database(db_name, action)
                elif db_type == 'graph':
                    from .cli_migrate import migrate_neo4j
                    neo4j_action = action if action in ['migrate', 'info', 'validate', 'clean'] else 'migrate'
                    result = migrate_neo4j(neo4j_action)
                elif db_type == 'search':
                    from .cli_migrate import migrate_elasticsearch
                    es_action = action if action in ['migrate', 'info'] else 'migrate'
                    result = migrate_elasticsearch(es_action)
                else:
                    console.print(f"[red]❌ Unknown database type: {db_type}[/red]")
                    success = False
                    continue
                
                if result:
                    console.print(f"[green]✅ {db_name} migration completed[/green]")
                else:
                    console.print(f"[red]❌ {db_name} migration failed[/red]")
                    success = False
            except Exception as e:
                console.print(f"[red]❌ Error migrating {db_name}: {e}[/red]")
                success = False
        
        if dry_run:
            console.print("\n[yellow]💡 Run without --dry-run to execute the migrations[/yellow]")
            return
        elif success:
            console.print("\n[green]🎉 All database migrations completed successfully![/green]")
        else:
            console.print("\n[red]💥 Some migrations failed. Check the logs above.[/red]")
            ctx.exit(1)
        return
    
    # Validate database exists and is managed
    if not is_database_managed(database):
        console.print(f"[red]❌ Database '{database}' is not managed by weave or doesn't exist[/red]")
        ctx.exit(1)
    
    db_type = get_database_type(database)
    migration_tool = get_database_migration_tool(database)
    
    if dry_run:
        console.print(f"[blue]📋 Would migrate {database} database:[/blue]")
        console.print(f"  • Type: {db_type}")
        console.print(f"  • Tool: {migration_tool}")
        console.print(f"  • Action: {action}")
        console.print()
        console.print("[yellow]💡 Run without --dry-run to execute the migration[/yellow]")
        return
    
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
    
    # Implement rollback logic directly
    from .config import get_database_type
    
    db_type = get_database_type(database)
    
    try:
        if db_type == 'sql':
            # Use Alembic for SQL databases
            from .cli_migrate import migrate_database
            action = 'downgrade'
            if revision:
                action = f'downgrade {revision}'
            else:
                action = 'downgrade -1'  # Rollback one migration
            
            console.print(f"[bold yellow]🔄 Rolling back {database} database[/bold yellow]")
            result = migrate_database(database, action)
            
            if result:
                console.print(f"[green]✅ {database} rollback completed successfully[/green]")
            else:
                console.print(f"[red]❌ {database} rollback failed[/red]")
                ctx.exit(1)
        else:
            console.print(f"[red]❌ Rollback not supported for {db_type} databases[/red]")
            ctx.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error rolling back {database}: {e}[/red]")
        ctx.exit(1)

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
    # Implement status logic directly
    from .config import (get_managed_databases, get_database_type, 
                        get_database_migration_tool)
    from rich.table import Table
    
    try:
        if database == 'all':
            table = Table(title="Database Migration Status")
            table.add_column("Database", style="cyan", no_wrap=True)
            table.add_column("Type", style="blue")
            table.add_column("Status", style="green")
            
            for db in get_managed_databases():
                try:
                    db_type = get_database_type(db)
                    
                    if db_type == 'sql':
                        # Use Alembic for SQL databases
                        from .cli_migrate import show_current_revision
                        revision = show_current_revision(db).strip()
                        status = revision if revision else "[yellow]No migrations applied[/yellow]"
                    elif db_type == 'graph':
                        # Get Neo4j migration status
                        from .cli_migrate import get_neo4j_migration_status
                        neo4j_status = get_neo4j_migration_status()
                        status = neo4j_status if neo4j_status else "[yellow]No migrations found[/yellow]"
                    elif db_type == 'search':
                        # Get Elasticsearch migration status
                        from .cli_migrate import get_elasticsearch_migration_status
                        es_status = get_elasticsearch_migration_status()
                        status = es_status if es_status else "[yellow]No migrations applied[/yellow]"
                    else:
                        status = "[red]Unknown database type[/red]"
                    
                    table.add_row(db, db_type or "unknown", status)
                except Exception as e:
                    table.add_row(db, "error", f"[red]Error: {str(e)}[/red]")
            
            console.print(table)
        else:
            from .config import get_database_type
            
            db_type = get_database_type(database)
            
            console.print(f"[bold blue]{database} database status:[/bold blue]")
            console.print(f"[blue]Type: {db_type}[/blue]")
            
            if db_type == 'sql':
                # Use Alembic for SQL databases
                from .cli_migrate import show_current_revision
                revision = show_current_revision(database)
                if revision.strip():
                    console.print(f"[green]Current revision: {revision.strip()}[/green]")
                else:
                    console.print("[yellow]No migrations applied[/yellow]")
            elif db_type == 'graph':
                # Get Neo4j migration status
                from .cli_migrate import get_neo4j_migration_status
                neo4j_status = get_neo4j_migration_status()
                if neo4j_status:
                    console.print(f"Status: {neo4j_status}")
                else:
                    console.print("[yellow]No migrations found[/yellow]")
            elif db_type == 'search':
                # Get Elasticsearch migration status
                from .cli_migrate import get_elasticsearch_migration_status
                es_status = get_elasticsearch_migration_status()
                if es_status:
                    console.print(f"Status: {es_status}")
                else:
                    console.print("[yellow]No migrations applied[/yellow]")
            else:
                console.print(f"[red]Unknown database type: {db_type}[/red]")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)

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
    # Implement history logic directly
    from .config import get_database_type
    
    try:
        db_type = get_database_type(database)
        console.print(f"[bold blue]{database} migration history:[/bold blue]")
        
        if db_type == 'sql':
            # Use Alembic for SQL databases
            from .cli_migrate import show_migration_history
            history = show_migration_history(database)
            console.print(history)
        elif db_type == 'graph':
            # Use neo4j-migrations for graph databases
            console.print("[blue]Running neo4j-migrations info command...[/blue]")
            from .cli_migrate import migrate_neo4j
            result = migrate_neo4j('info')
            if result:
                console.print(result)
            else:
                console.print("[yellow]No Neo4j migration history available[/yellow]")
        elif db_type == 'search':
            # Elasticsearch doesn't have a traditional history command
            console.print("[blue]Elasticsearch migration history:[/blue]")
            console.print("[yellow]Elasticsearch migrations are applied via HTTP requests.[/yellow]")
            console.print("[yellow]Check the .weave/migrations/elasticsearch/scripts/ directory for migration files.[/yellow]")
            
            # List migration files
            from pathlib import Path
            from .cli_migrate import get_project_root
            project_root = get_project_root()
            migrations_dir = project_root / '.weave' / 'migrations' / 'elasticsearch' / 'scripts'
            
            if migrations_dir.exists():
                migration_files = sorted(migrations_dir.glob("V*.http"))
                if migration_files:
                    console.print("\n[blue]Available migration files:[/blue]")
                    for migration_file in migration_files:
                        console.print(f"  • {migration_file.name}")
                else:
                    console.print("[yellow]No migration files found[/yellow]")
            else:
                console.print("[yellow]No Elasticsearch migrations directory found[/yellow]")
        else:
            console.print(f"[red]Unknown database type: {db_type}[/red]")
            console.print("[yellow]Cannot show migration history for this database type[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)

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
        from .config import get_database_type
        db_type = get_database_type(database)
        
        if db_type == 'sql':
            from .cli_migrate import migrate_database
            result = migrate_database(database, 'downgrade base')
            if result:
                console.print(f"[green]✅ Rolled back all migrations for {database}[/green]")
            else:
                console.print(f"[yellow]Warning during rollback for {database}[/yellow]")
        else:
            console.print(f"[yellow]Reset not supported for {db_type} databases[/yellow]")
            return
    except Exception as e:
        console.print(f"[yellow]Warning during rollback: {e}[/yellow]")
    
    # Then re-run all migrations
    try:
        from .cli_migrate import migrate_database
        result = migrate_database(database, 'upgrade')
        if result:
            console.print(f"[green]🎉 Database {database} has been reset successfully![/green]")
        else:
            console.print(f"[red]❌ Failed to re-run migrations for {database}[/red]")
            ctx.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error re-running migrations: {e}[/red]")
        ctx.exit(1)

@db_group.command('seed')
@click.argument('database', type=click.Choice(get_database_choices() + ['all']), default='all')
@click.pass_context
def db_seed(ctx, database):
    """Seed databases with sample data
    
    Examples:
    
    Seed all databases:
    weave db seed
    
    Seed specific database:
    weave db seed slack
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

# Add the tool subgroup to the db group
db_group.add_command(db_tool_group) 