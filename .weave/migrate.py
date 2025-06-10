#!/usr/bin/env python3
"""
Weave Migration Management Tool

This script provides commands to manage database migrations for the Insight Mesh project.
It uses Alembic to handle migrations for multiple databases in the consolidated PostgreSQL setup.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, cwd=None, env=None):
    """Run a shell command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def get_env():
    """Get environment variables for database connections"""
    env = os.environ.copy()
    
    # Set default values if not provided
    env.setdefault('POSTGRES_USER', 'postgres')
    env.setdefault('POSTGRES_PASSWORD', 'postgres')
    env.setdefault('POSTGRES_HOST', 'localhost')
    env.setdefault('POSTGRES_PORT', '5432')
    
    return env

def migrate_database(database_name, action='upgrade'):
    """Run migration for a specific database"""
    env = get_env()
    migrations_dir = Path(__file__).parent / 'migrations'
    
    # Set the database-specific environment
    env['DATABASE_NAME'] = database_name
    
    cmd = [
        'alembic',
        '-c', str(migrations_dir / 'alembic.ini'),
        '-x', f'database={database_name}',
        action
    ]
    
    if action == 'upgrade':
        cmd.append('head')
    
    return run_command(cmd, cwd=str(project_root), env=env)

def migrate_all(action='upgrade'):
    """Run migrations for all databases"""
    databases = ['mcp', 'insight_mesh']
    
    for db in databases:
        print(f"\n{'='*50}")
        print(f"Running {action} for {db} database")
        print(f"{'='*50}")
        migrate_database(db, action)
        print(f"✅ {action.capitalize()} completed for {db}")

def create_migration(database_name, message):
    """Create a new migration for a specific database"""
    env = get_env()
    migrations_dir = Path(__file__).parent / 'migrations'
    
    cmd = [
        'alembic',
        '-c', str(migrations_dir / 'alembic.ini'),
        '-x', f'database={database_name}',
        'revision',
        '--autogenerate',
        '-m', message
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def show_current_revision(database_name):
    """Show current revision for a database"""
    env = get_env()
    migrations_dir = Path(__file__).parent / 'migrations'
    
    cmd = [
        'alembic',
        '-c', str(migrations_dir / 'alembic.ini'),
        '-x', f'database={database_name}',
        'current'
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def show_migration_history(database_name):
    """Show migration history for a database"""
    env = get_env()
    migrations_dir = Path(__file__).parent / 'migrations'
    
    cmd = [
        'alembic',
        '-c', str(migrations_dir / 'alembic.ini'),
        '-x', f'database={database_name}',
        'history'
    ]
    
    return run_command(cmd, cwd=str(project_root), env=env)

def main():
    parser = argparse.ArgumentParser(description='Weave Migration Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
    migrate_parser.add_argument('--database', '-d', choices=['mcp', 'insight_mesh', 'all'], 
                               default='all', help='Database to migrate')
    migrate_parser.add_argument('--action', choices=['upgrade', 'downgrade'], 
                               default='upgrade', help='Migration action')
    
    # Create migration command
    create_parser = subparsers.add_parser('create', help='Create a new migration')
    create_parser.add_argument('database', choices=['mcp', 'insight_mesh'], 
                              help='Database for the migration')
    create_parser.add_argument('message', help='Migration message')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    status_parser.add_argument('--database', '-d', choices=['mcp', 'insight_mesh', 'all'], 
                              default='all', help='Database to check')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show migration history')
    history_parser.add_argument('database', choices=['mcp', 'insight_mesh'], 
                               help='Database to show history for')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'migrate':
            if args.database == 'all':
                migrate_all(args.action)
            else:
                migrate_database(args.database, args.action)
                
        elif args.command == 'create':
            create_migration(args.database, args.message)
            
        elif args.command == 'status':
            if args.database == 'all':
                for db in ['mcp', 'insight_mesh']:
                    print(f"\n{db} database:")
                    print(show_current_revision(db))
            else:
                print(show_current_revision(args.database))
                
        elif args.command == 'history':
            print(show_migration_history(args.database))
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 