"""Create databases

Revision ID: 000
Revises: 
Create Date: 2024-01-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the required databases if they don't exist"""
    
    # Get a connection to the default postgres database
    connection = op.get_bind()
    
    # List of databases to create
    databases = ['openwebui', 'litellm', 'mcp', 'insight_mesh']
    
    for db_name in databases:
        # Check if database exists
        result = connection.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = :db_name"
        ), {"db_name": db_name})
        
        if not result.fetchone():
            # Database doesn't exist, create it
            # Note: We need to commit the current transaction and start a new one
            # because CREATE DATABASE cannot run inside a transaction block
            connection.execute(text("COMMIT"))
            connection.execute(text(f"CREATE DATABASE {db_name}"))
            connection.execute(text("BEGIN"))
            print(f"Created database: {db_name}")
        else:
            print(f"Database already exists: {db_name}")


def downgrade() -> None:
    """Drop the databases (use with caution!)"""
    
    # Get a connection to the default postgres database
    connection = op.get_bind()
    
    # List of databases to drop (excluding system databases)
    databases = ['openwebui', 'litellm', 'mcp', 'insight_mesh']
    
    for db_name in databases:
        # Check if database exists
        result = connection.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = :db_name"
        ), {"db_name": db_name})
        
        if result.fetchone():
            # Database exists, drop it
            # Note: We need to commit the current transaction and start a new one
            # because DROP DATABASE cannot run inside a transaction block
            connection.execute(text("COMMIT"))
            
            # Terminate any existing connections to the database
            connection.execute(text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
            """))
            
            connection.execute(text(f"DROP DATABASE {db_name}"))
            connection.execute(text("BEGIN"))
            print(f"Dropped database: {db_name}")
        else:
            print(f"Database doesn't exist: {db_name}") 