import logging
import os
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slack.models import Base, SlackUser, SlackChannel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackPostgresService:
    """Service for handling PostgreSQL operations for Slack data.
    
    Note: Database migrations are managed centrally by Weave (.weave/migrations/slack/).
    This service assumes the database schema is already set up and does not run migrations.
    """
    
    def __init__(self):
        # Get connection parameters from environment variables with sensible defaults
        pg_host = os.getenv("POSTGRES_HOST", "postgres_dagster")  # Point to our dedicated postgres
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        pg_dbname = os.getenv("SLACK_DBNAME", "slack")
        
        # Connection string for our application database
        self.conn_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_dbname}"
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Connecting to PostgreSQL at {pg_host}:{pg_port}/{pg_dbname}")
        
        # Initialize SQLAlchemy
        self.engine = create_engine(self.conn_string)
        self.Session = sessionmaker(bind=self.engine)


    
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
                    # Skip users with empty emails to avoid unique constraint violations
                    # Bots often have empty emails, so we need to handle this case
                    if not user_data.get('email') and user_data.get('is_bot', False):
                        self.logger.info(f"Skipping bot user without email: {user_data.get('name', 'unknown')}")
                        continue
                        
                    # Add a unique identifier to empty emails to avoid conflicts
                    if not user_data.get('email'):
                        user_data['email'] = f"bot-{user_data.get('id')}@example.com"
                        self.logger.info(f"Generated placeholder email for: {user_data.get('name')}")
                    
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
            
            import datetime
            import json
            import copy
            
            for channel_data in channels:
                try:
                    # Make a deep copy to avoid modifying the original data
                    channel_for_db = copy.deepcopy(channel_data)
                    
                    # Convert Unix timestamp to datetime for database storage
                    created_timestamp = None
                    if 'created' in channel_for_db and channel_for_db['created'] and isinstance(channel_for_db['created'], int):
                        created_timestamp = datetime.datetime.fromtimestamp(
                            channel_for_db['created'], 
                            tz=datetime.timezone.utc
                        )
                    
                    # Check if channel already exists
                    channel = session.query(SlackChannel).filter_by(id=channel_for_db.get('id')).first()
                    
                    if channel:
                        # Update existing channel
                        channel.name = channel_for_db.get('name')
                        channel.is_private = channel_for_db.get('is_private', False)
                        channel.is_archived = channel_for_db.get('is_archived', False)
                        channel.created = created_timestamp  # Use the converted timestamp
                        channel.creator = channel_for_db.get('creator')
                        channel.num_members = channel_for_db.get('num_members', 0)
                        channel.purpose = channel_for_db.get('purpose', {}).get('value') if channel_for_db.get('purpose') else None
                        channel.topic = channel_for_db.get('topic', {}).get('value') if channel_for_db.get('topic') else None
                        channel.data = channel_data  # Store original data for JSON
                    else:
                        # Create new channel
                        channel = SlackChannel(
                            id=channel_for_db.get('id'),
                            name=channel_for_db.get('name'),
                            is_private=channel_for_db.get('is_private', False),
                            is_archived=channel_for_db.get('is_archived', False),
                            created=created_timestamp,  # Use the converted timestamp
                            creator=channel_for_db.get('creator'),
                            num_members=channel_for_db.get('num_members', 0),
                            purpose=channel_for_db.get('purpose', {}).get('value') if channel_for_db.get('purpose') else None,
                            topic=channel_for_db.get('topic', {}).get('value') if channel_for_db.get('topic') else None,
                            data=channel_data  # Store original data for JSON
                        )
                        session.add(channel)
                    
                    stored_count += 1
                except Exception as e:
                    self.logger.error(f"Error storing channel {channel_for_db.get('name')}: {e}")
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