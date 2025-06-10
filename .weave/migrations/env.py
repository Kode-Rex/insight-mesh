import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the project root to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import all models for autogenerate support
from mcp_server.database import Base as MCPBase
from dagster_project.slack.models import Base as SlackBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Define target metadata for each database
databases = {
    'openwebui': None,  # OpenWebUI manages its own schema
    'litellm': None,    # LiteLLM manages its own schema
    'mcp': MCPBase.metadata,
    'insight_mesh': SlackBase.metadata,
}

def get_database_url(database_name: str) -> str:
    """Get database URL from environment variables"""
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{database_name}"



def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    # Get the database name from command line or default to all
    database = context.get_x_argument(as_dictionary=True).get('database', 'all')
    
    if database == 'all':
        # Run migrations for all databases
        for db_name, target_metadata in databases.items():
            if target_metadata is not None:
                url = get_database_url(db_name)
                context.configure(
                    url=url,
                    target_metadata=target_metadata,
                    literal_binds=True,
                    dialect_opts={"paramstyle": "named"},
                    version_table=f"alembic_version_{db_name}"
                )
                
                with context.begin_transaction():
                    context.run_migrations()
    else:
        # Run migration for specific database
        if database in databases and databases[database] is not None:
            url = get_database_url(database)
            context.configure(
                url=url,
                target_metadata=databases[database],
                literal_binds=True,
                dialect_opts={"paramstyle": "named"},
                version_table=f"alembic_version_{database}"
            )
            
            with context.begin_transaction():
                context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Get the database name from command line or default to all
    database = context.get_x_argument(as_dictionary=True).get('database', 'all')
    
    if database == 'all':
        # Run migrations for all databases
        for db_name, target_metadata in databases.items():
            if target_metadata is not None:
                url = get_database_url(db_name)
                connectable = engine_from_config(
                    {'sqlalchemy.url': url},
                    prefix="sqlalchemy.",
                    poolclass=pool.NullPool,
                )
                
                with connectable.connect() as connection:
                    context.configure(
                        connection=connection,
                        target_metadata=target_metadata,
                        version_table=f"alembic_version_{db_name}"
                    )
                    
                    with context.begin_transaction():
                        context.run_migrations()
    else:
        # Run migration for specific database
        if database in databases and databases[database] is not None:
            url = get_database_url(database)
            connectable = engine_from_config(
                {'sqlalchemy.url': url},
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
            
            with connectable.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=databases[database],
                    version_table=f"alembic_version_{database}"
                )
                
                with context.begin_transaction():
                    context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 