#!/usr/bin/env python

import os
import sys
import subprocess
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .config import get_managed_databases, get_all_databases, get_database_choices
from typing import List, Dict

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

def migrate_neo4j(action='info'):
    """Run Neo4j migrations using neo4j-migrations tool"""
    env = get_env()
    project_root = get_project_root()
    
    # Check if neo4j-migrations CLI is available
    neo4j_migrations_cmd = 'neo4j-migrations'
    
    cmd = [neo4j_migrations_cmd]
    
    if action == 'info':
        cmd.append('info')
    elif action == 'migrate':
        cmd.append('migrate')
    elif action == 'validate':
        cmd.append('validate')
    elif action == 'clean':
        cmd.append('clean')
    
    # Add configuration file
    cmd.extend(['-c', str(project_root / '.weave' / 'migrations' / 'neo4j' / 'neo4j.conf')])
    
    console.print(f"[blue]🔄 Running Neo4j migration: {action}[/blue]")
    return run_command(cmd, cwd=str(project_root), env=env)

def migrate_elasticsearch(action='migrate'):
    """Run Elasticsearch migrations using elasticsearch-evolution"""
    env = get_env()
    project_root = get_project_root()
    
    # Use elasticsearch-evolution via Docker or JAR
    # For simplicity, using curl to apply HTTP-based migrations
    if action == 'migrate':
        console.print("[blue]🔄 Running Elasticsearch migrations[/blue]")
        
        # Read and execute migration files
        migrations_dir = project_root / '.weave' / 'migrations' / 'elasticsearch' / 'scripts'
        
        if not migrations_dir.exists():
            console.print("[yellow]⚠️  No Elasticsearch migrations directory found[/yellow]")
            return True
        
        # Get Elasticsearch connection details
        es_host = env.get('ELASTICSEARCH_HOST', 'localhost')
        es_port = env.get('ELASTICSEARCH_PORT', '9200')
        es_url = f"http://{es_host}:{es_port}"
        
        # Apply migrations in order
        for migration_file in sorted(migrations_dir.glob("V*.http")):
            console.print(f"[blue]📄 Applying migration: {migration_file.name}[/blue]")
            
            # Parse and execute HTTP requests from the migration file
            # This is a simplified version - in production, use elasticsearch-evolution
            try:
                with open(migration_file, 'r') as f:
                    content = f.read()
                
                # Extract HTTP requests (simplified parser)
                requests = parse_http_migration_file(content, es_url)
                
                for request in requests:
                    result = execute_http_request(request)
                    if not result:
                        console.print(f"[red]❌ Failed to apply migration: {migration_file.name}[/red]")
                        return False
                
                console.print(f"[green]✅ Applied migration: {migration_file.name}[/green]")
                
            except Exception as e:
                console.print(f"[red]❌ Error applying migration {migration_file.name}: {e}[/red]")
                return False
        
        console.print("[green]✅ All Elasticsearch migrations applied successfully[/green]")
        return True
    
    elif action == 'info':
        # Show current state
        console.print("[blue]📊 Elasticsearch migration info[/blue]")
        # Implementation would check which indices exist
        return True

def parse_http_migration_file(content: str, base_url: str) -> List[Dict]:
    """Parse HTTP migration file and return list of requests"""
    import re
    import json
    
    requests = []
    
    # Split by ### markers
    sections = re.split(r'###[^\n]*\n', content)
    
    for section in sections[1:]:  # Skip first empty section
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        if len(lines) < 2:
            continue
            
        # Parse HTTP method and path
        method_line = lines[0].strip()
        if not method_line:
            continue
            
        parts = method_line.split(' ', 1)
        if len(parts) != 2:
            continue
            
        method, path = parts
        url = f"{base_url}{path}"
        
        # Find Content-Type and JSON body
        headers = {}
        body = None
        json_start = -1
        
        for i, line in enumerate(lines[1:], 1):
            if line.startswith('Content-Type:'):
                headers['Content-Type'] = line.split(':', 1)[1].strip()
            elif line.strip() == '{':
                json_start = i
                break
        
        if json_start > 0:
            json_lines = lines[json_start:]
            try:
                body = json.loads('\n'.join(json_lines))
            except json.JSONDecodeError:
                continue
        
        requests.append({
            'method': method,
            'url': url,
            'headers': headers,
            'json': body
        })
    
    return requests

def execute_http_request(request: Dict) -> bool:
    """Execute HTTP request for Elasticsearch migration"""
    import requests as http_requests
    
    try:
        response = http_requests.request(
            method=request['method'],
            url=request['url'],
            headers=request.get('headers', {}),
            json=request.get('json')
        )
        
        if response.status_code in [200, 201]:
            return True
        elif response.status_code == 400:
            # Check if it's a "resource already exists" error
            error_response = response.json()
            if 'resource_already_exists_exception' in str(error_response):
                console.print(f"[yellow]⚠️  Resource already exists, skipping[/yellow]")
                return True
        
        console.print(f"[red]❌ HTTP {response.status_code}: {response.text}[/red]")
        return False
        
    except Exception as e:
        console.print(f"[red]❌ Request failed: {e}[/red]")
        return False

def get_neo4j_migration_status() -> str:
    """Get Neo4j migration status using neo4j-migrations info command"""
    env = get_env()
    project_root = get_project_root()
    
    # Check if neo4j-migrations CLI is available
    neo4j_migrations_cmd = 'neo4j-migrations'
    
    cmd = [
        neo4j_migrations_cmd, 'info',
        '-c', str(project_root / '.weave' / 'migrations' / 'neo4j' / 'neo4j.conf')
    ]
    
    try:
        result = run_command(cmd, cwd=str(project_root), env=env)
        if result:
            # Parse the output to extract meaningful status
            lines = result.strip().split('\n')
            for line in lines:
                if 'Applied migrations:' in line or 'Current version:' in line:
                    return line.strip()
            # If no specific status found, return a summary
            return f"{len(lines)} migration entries"
        return "No status available"
    except Exception as e:
        if "No such file or directory" in str(e):
            return "[yellow]neo4j-migrations not installed (run: weave db install-tools)[/yellow]"
        else:
            return f"[red]Error: {str(e)}[/red]"

def get_elasticsearch_migration_status() -> str:
    """Get Elasticsearch migration status by checking indices"""
    env = get_env()
    
    # Get Elasticsearch connection details
    es_host = env.get('ELASTICSEARCH_HOST', 'localhost')
    es_port = env.get('ELASTICSEARCH_PORT', '9200')
    es_url = f"http://{es_host}:{es_port}"
    
    try:
        import requests as http_requests
        
        # Check cluster health and indices
        response = http_requests.get(f"{es_url}/_cat/indices?v&format=json", timeout=5)
        if response.status_code == 200:
            indices = response.json()
            if indices:
                return f"{len(indices)} indices created"
            else:
                return "No indices found"
        else:
            return f"[yellow]HTTP {response.status_code} - Elasticsearch not responding[/yellow]"
    except ImportError:
        return "[yellow]requests library not installed (run: weave db install-tools)[/yellow]"
    except Exception as e:
        if "Connection" in str(e) or "timeout" in str(e).lower():
            return "[yellow]Elasticsearch not running or not accessible[/yellow]"
        else:
            return f"[red]Error: {str(e)}[/red]"

def install_python_dependencies():
    """Install Python dependencies for migrations"""
    project_root = get_project_root()
    requirements_file = project_root / 'requirements-migrations.txt'
    
    if not requirements_file.exists():
        console.print(f"[red]❌ Requirements file not found: {requirements_file}[/red]")
        return False
    
    console.print("[blue]📦 Installing Python migration dependencies...[/blue]")
    
    try:
        cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✅ Python dependencies installed successfully[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to install Python dependencies: {result.stderr}[/red]")
            return False
    except Exception as e:
        console.print(f"[red]❌ Error installing Python dependencies: {e}[/red]")
        return False

def install_neo4j_migrations():
    """Install neo4j-migrations CLI tool"""
    console.print("[blue]📦 Installing neo4j-migrations CLI tool...[/blue]")
    
    # Check if Java is available, if not try to install OpenJDK
    java_available = False
    try:
        # Java -version outputs to stderr, not stdout
        java_result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if java_result.returncode == 0:
            version_info = java_result.stderr.split()[2] if java_result.stderr else 'version unknown'
            console.print(f"[green]✅ Java detected: {version_info}[/green]")
            java_available = True
    except FileNotFoundError:
        pass
    
    if not java_available:
        console.print("[yellow]⚠️  Java not found. Attempting to install OpenJDK...[/yellow]")
        
        # Try to install OpenJDK via Homebrew (macOS)
        try:
            brew_check = subprocess.run(['brew', '--version'], capture_output=True, text=True)
            if brew_check.returncode == 0:
                console.print("[blue]📦 Installing OpenJDK via Homebrew...[/blue]")
                install_result = subprocess.run(['brew', 'install', 'openjdk'], capture_output=True, text=True)
                
                if install_result.returncode == 0:
                    console.print("[green]✅ OpenJDK installed successfully![/green]")
                    
                    # Verify Java is now available
                    java_verify = subprocess.run(['java', '-version'], capture_output=True, text=True)
                    if java_verify.returncode == 0:
                        java_available = True
                        version_info = java_verify.stderr.split()[2] if java_verify.stderr else 'version unknown'
                        console.print(f"[green]✅ Java now available: {version_info}[/green]")
                    else:
                        console.print("[yellow]⚠️  OpenJDK installed but may need PATH configuration[/yellow]")
                        console.print("[blue]💡 Try: export PATH=\"/opt/homebrew/opt/openjdk/bin:$PATH\"[/blue]")
                else:
                    console.print(f"[yellow]⚠️  Failed to install OpenJDK via Homebrew: {install_result.stderr}[/yellow]")
        except FileNotFoundError:
            pass
    
    if not java_available:
        console.print("[red]❌ Java/OpenJDK is required for neo4j-migrations.[/red]")
        console.print("[blue]📖 Installation options:[/blue]")
        console.print("  1. Homebrew (macOS): brew install openjdk")
        console.print("  2. SDKMAN: sdk install java")
        console.print("  3. Download from: https://adoptium.net/")
        console.print("  4. Use Docker alternative: docker run --rm neo4j/neo4j-migrations")
        return False
    
    # Try to install via different methods
    install_methods = [
        {
            'name': 'Homebrew (macOS)',
            'check': ['brew', '--version'],
            'install': ['brew', 'install', 'neo4j-migrations']
        },
        {
            'name': 'SDKMAN',
            'check': ['sdk', 'version'],
            'install': ['sdk', 'install', 'neo4j-migrations']
        }
    ]
    
    for method in install_methods:
        try:
            # Check if the package manager is available
            check_result = subprocess.run(method['check'], capture_output=True, text=True)
            if check_result.returncode == 0:
                console.print(f"[blue]📦 Installing via {method['name']}...[/blue]")
                
                install_result = subprocess.run(method['install'], capture_output=True, text=True)
                if install_result.returncode == 0:
                    console.print(f"[green]✅ neo4j-migrations installed via {method['name']}[/green]")
                    return True
                else:
                    console.print(f"[yellow]⚠️  Failed to install via {method['name']}: {install_result.stderr}[/yellow]")
        except FileNotFoundError:
            continue
    
    # If all methods fail, provide manual installation instructions
    console.print("[yellow]⚠️  Automatic installation failed. Manual installation required:[/yellow]")
    console.print("[blue]📖 Installation options:[/blue]")
    console.print("  1. Homebrew (macOS): brew install neo4j-migrations")
    console.print("  2. SDKMAN: sdk install neo4j-migrations")
    console.print("  3. Download JAR: https://github.com/michael-simons/neo4j-migrations/releases")
    console.print("  4. Docker: Use the migration Docker image")
    
    return False

def check_and_install_tools():
    """Check for required tools and offer to install them"""
    console.print("[blue]🔍 Checking migration tools...[/blue]")
    
    tools_status = {
        'python_deps': False,
        'neo4j_migrations': False
    }
    
    # Check Python dependencies
    try:
        import requests
        tools_status['python_deps'] = True
        console.print("[green]✅ Python dependencies available[/green]")
    except ImportError:
        console.print("[yellow]⚠️  Python dependencies missing[/yellow]")
    
    # Check neo4j-migrations
    try:
        result = subprocess.run(['neo4j-migrations', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            tools_status['neo4j_migrations'] = True
            console.print("[green]✅ neo4j-migrations available[/green]")
    except FileNotFoundError:
        console.print("[yellow]⚠️  neo4j-migrations not found[/yellow]")
    
    # Offer to install missing tools
    missing_tools = [k for k, v in tools_status.items() if not v]
    
    if missing_tools:
        console.print(f"\n[yellow]📦 Missing tools: {', '.join(missing_tools)}[/yellow]")
        
        if click.confirm("Would you like to install the missing tools?"):
            success = True
            
            if not tools_status['python_deps']:
                success &= install_python_dependencies()
            
            if not tools_status['neo4j_migrations']:
                success &= install_neo4j_migrations()
            
            return success
        else:
            console.print("[blue]ℹ️  You can install tools later with: weave db install-tools[/blue]")
            return False
    else:
        console.print("[green]🎉 All migration tools are available![/green]")
        return True

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
            from .config import (get_managed_databases, get_database_type, 
                               get_database_migration_tool)
            
            table = Table(title="Database Migration Status")
            table.add_column("Database", style="cyan", no_wrap=True)
            table.add_column("Type", style="blue")
            table.add_column("Tool", style="yellow")
            table.add_column("Status", style="green")
            
            for db in get_managed_databases():
                try:
                    db_type = get_database_type(db)
                    migration_tool = get_database_migration_tool(db)
                    
                    if db_type == 'sql':
                        # Use Alembic for SQL databases
                        revision = show_current_revision(db).strip()
                        status = revision if revision else "[yellow]No migrations applied[/yellow]"
                    elif db_type == 'graph':
                        # Get Neo4j migration status
                        neo4j_status = get_neo4j_migration_status()
                        status = neo4j_status if neo4j_status else "[yellow]No migrations applied[/yellow]"
                    elif db_type == 'search':
                        # Get Elasticsearch migration status
                        es_status = get_elasticsearch_migration_status()
                        status = es_status if es_status else "[yellow]No migrations applied[/yellow]"
                    else:
                        status = "[red]Unknown database type[/red]"
                    
                    table.add_row(db, db_type or "unknown", migration_tool or "none", status)
                except Exception as e:
                    table.add_row(db, "error", "error", f"[red]Error: {str(e)}[/red]")
            
            console.print(table)
        else:
            from .config import get_database_type, get_database_migration_tool
            
            db_type = get_database_type(database)
            migration_tool = get_database_migration_tool(database)
            
            console.print(f"[bold blue]{database} database status:[/bold blue]")
            console.print(f"[blue]Type: {db_type}[/blue]")
            console.print(f"[blue]Migration Tool: {migration_tool}[/blue]")
            
            if db_type == 'sql':
                # Use Alembic for SQL databases
                revision = show_current_revision(database)
                if revision.strip():
                    console.print(f"[green]Current revision: {revision.strip()}[/green]")
                else:
                    console.print("[yellow]No migrations applied[/yellow]")
            elif db_type == 'graph':
                # Get Neo4j migration status
                neo4j_status = get_neo4j_migration_status()
                if neo4j_status:
                    console.print(f"Status: {neo4j_status}")
                else:
                    console.print("[yellow]No migrations applied[/yellow]")
            elif db_type == 'search':
                # Get Elasticsearch migration status
                es_status = get_elasticsearch_migration_status()
                if es_status:
                    console.print(f"Status: {es_status}")
                else:
                    console.print("[yellow]No migrations applied[/yellow]")
            else:
                console.print(f"[red]Unknown database type: {db_type}[/red]")
                
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