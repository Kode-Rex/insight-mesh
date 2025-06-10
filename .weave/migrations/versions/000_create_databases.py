"""Create databases

Revision ID: 000
Revises: 
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def get_database_connection():
    """Get connection to the default postgres database"""
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    
    conn = psycopg2.connect(
        host=postgres_host,
        port=postgres_port,
        user=postgres_user,
        password=postgres_password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def upgrade() -> None:
    """Create the required databases if they don't exist"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # List of databases to create
    databases = ['openwebui', 'litellm', 'mcp', 'insight_mesh']
    
    for db_name in databases:
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        if not cursor.fetchone():
            # Database doesn't exist, create it
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database: {db_name}")
        else:
            print(f"Database already exists: {db_name}")
    
    cursor.close()
    conn.close()


def downgrade() -> None:
    """Drop the databases (use with caution!)"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # List of databases to drop (in reverse order)
    databases = ['insight_mesh', 'mcp', 'litellm', 'openwebui']
    
    for db_name in databases:
        # Terminate connections to the database first
        cursor.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
        """)
        
        # Drop the database
        cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        print(f"Dropped database: {db_name}")
    
    cursor.close()
    conn.close() 