import logging
import os
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, Any, List, Optional
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.config import Config as AlembicConfig
from alembic import command

from slack.models import Base, SlackUser, SlackChannel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackPostgresService:
    """Service for handling PostgreSQL operations for Slack data."""
    
    def __init__(self):
        # Get connection parameters from environment variables with sensible defaults
        pg_host = os.getenv("POSTGRES_HOST", "insight_postgres")  # Point to our dedicated postgres
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        pg_dbname = os.getenv("POSTGRES_DBNAME", "insight_mesh")
        
        # Connection string for our application database
        self.conn_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_dbname}"
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Connecting to PostgreSQL at {pg_host}:{pg_port}/{pg_dbname}")
        
        # Initialize SQLAlchemy
        self.engine = create_engine(self.conn_string)
        self.Session = sessionmaker(bind=self.engine)
        
        # Run migrations
        self._run_migrations()

    def _run_migrations(self):
        """Run database migrations using Alembic."""
        try:
            self.logger.info("Running database migrations")
            # Get the path to the alembic.ini file
            alembic_ini_path = Path(__file__).parent.parent / "migrations" / "alembic.ini"
            
            # Create Alembic config
            alembic_cfg = AlembicConfig(str(alembic_ini_path))
            
            # Override the sqlalchemy.url in the config
            alembic_cfg.set_main_option("sqlalchemy.url", self.conn_string)
            
            # Run the migrations
            command.upgrade(alembic_cfg, "head")
            
            self.logger.info("Database migrations completed successfully")
        except Exception as e:
            self.logger.error(f"Error running migrations: {e}")
            raise
    
    def _get_connection(self):
        """Get a connection to the PostgreSQL database using psycopg2."""
        return psycopg2.connect(self.conn_string)
    
    def store_users(self, users: List[Dict[str, Any]]):
        """Store multiple Slack users in PostgreSQL using SQLAlchemy."""
        try:
            session = self.Session()
            stored_count = 0
            
            for user_data in users:
                try:
                    # Check if user already exists
                    user = session.query(SlackUser).filter_by(id=user_data.get('id')).first()
                    
                    if user:
                        # Update existing user
                        user.name = user_data.get('name')
                        user.real_name = user_data.get('real_name')
                        user.display_name = user_data.get('display_name')
                        user.email = user_data.get('email')
                        user.is_admin = user_data.get('is_admin', False)
                        user.is_owner = user_data.get('is_owner', False)
                        user.is_bot = user_data.get('is_bot', False)
                        user.deleted = user_data.get('deleted', False)
                        user.team_id = user_data.get('team_id')
                        user.data = user_data
                    else:
                        # Create new user
                        user = SlackUser(
                            id=user_data.get('id'),
                            name=user_data.get('name'),
                            real_name=user_data.get('real_name'),
                            display_name=user_data.get('display_name'),
                            email=user_data.get('email'),
                            is_admin=user_data.get('is_admin', False),
                            is_owner=user_data.get('is_owner', False),
                            is_bot=user_data.get('is_bot', False),
                            deleted=user_data.get('deleted', False),
                            team_id=user_data.get('team_id'),
                            data=user_data
                        )
                        session.add(user)
                    
                    stored_count += 1
                except Exception as e:
                    self.logger.error(f"Error storing user {user_data.get('name')}: {e}")
                    # Continue with next user
            
            session.commit()
            self.logger.info(f"Stored {stored_count} users in PostgreSQL")
            
        except Exception as e:
            self.logger.error(f"Error storing users in PostgreSQL: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def store_channels(self, channels: List[Dict[str, Any]]):
        """Store multiple Slack channels in PostgreSQL using SQLAlchemy."""
        try:
            session = self.Session()
            stored_count = 0
            
            for channel_data in channels:
                try:
                    # Check if channel already exists
                    channel = session.query(SlackChannel).filter_by(id=channel_data.get('id')).first()
                    
                    if channel:
                        # Update existing channel
                        channel.name = channel_data.get('name')
                        channel.is_private = channel_data.get('is_private', False)
                        channel.is_archived = channel_data.get('is_archived', False)
                        channel.created = channel_data.get('created')
                        channel.creator = channel_data.get('creator')
                        channel.num_members = channel_data.get('num_members', 0)
                        channel.purpose = channel_data.get('purpose', {}).get('value') if channel_data.get('purpose') else None
                        channel.topic = channel_data.get('topic', {}).get('value') if channel_data.get('topic') else None
                        channel.data = channel_data
                    else:
                        # Create new channel
                        channel = SlackChannel(
                            id=channel_data.get('id'),
                            name=channel_data.get('name'),
                            is_private=channel_data.get('is_private', False),
                            is_archived=channel_data.get('is_archived', False),
                            created=channel_data.get('created'),
                            creator=channel_data.get('creator'),
                            num_members=channel_data.get('num_members', 0),
                            purpose=channel_data.get('purpose', {}).get('value') if channel_data.get('purpose') else None,
                            topic=channel_data.get('topic', {}).get('value') if channel_data.get('topic') else None,
                            data=channel_data
                        )
                        session.add(channel)
                    
                    stored_count += 1
                except Exception as e:
                    self.logger.error(f"Error storing channel {channel_data.get('name')}: {e}")
                    # Continue with next channel
            
            session.commit()
            self.logger.info(f"Stored {stored_count} channels in PostgreSQL")
            
        except Exception as e:
            self.logger.error(f"Error storing channels in PostgreSQL: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email using SQLAlchemy."""
        try:
            session = self.Session()
            user = session.query(SlackUser).filter_by(email=email).first()
            return user.data if user else None
        except Exception as e:
            self.logger.error(f"Error getting user by email from PostgreSQL: {e}")
            raise
        finally:
            session.close()
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users using SQLAlchemy."""
        try:
            session = self.Session()
            users = session.query(SlackUser).all()
            return [user.data for user in users]
        except Exception as e:
            self.logger.error(f"Error getting all users from PostgreSQL: {e}")
            raise
        finally:
            session.close() 