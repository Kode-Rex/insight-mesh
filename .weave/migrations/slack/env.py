import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine, text
from sqlalchemy.exc import OperationalError
from alembic import context

# Add the project root to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import the SlackBase metadata for slack schema
from domain.data.slack import SlackBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for slack
target_metadata = SlackBase.metadata

def get_database_url() -> str:
    """Get database URL from environment variables"""
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/slack"

def ensure_database_exists():
    """Create the slack database if it doesn't exist"""
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    
    # Connect to the default postgres database to create slack database
    admin_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/postgres"
    
    try:
        admin_engine = create_engine(admin_url, isolation_level='AUTOCOMMIT')
        with admin_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'slack'"))
            if not result.fetchone():
                # Create the database
                conn.execute(text("CREATE DATABASE slack"))
                print("Created slack database")
            else:
                print("slack database already exists")
        admin_engine.dispose()
    except Exception as e:
        print(f"Warning: Could not ensure slack database exists: {e}")
        # Continue anyway - maybe it exists or will be created by Docker

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version_slack"
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Ensure the database exists before trying to connect
    ensure_database_exists()
    
    url = get_database_url()
    connectable = engine_from_config(
        {'sqlalchemy.url': url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_slack"
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 