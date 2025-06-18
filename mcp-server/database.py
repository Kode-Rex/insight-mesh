from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func, select
from typing import Optional, List
import os
from datetime import datetime
import asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import DisconnectionError, InterfaceError

# Import data objects instead of defining our own
from domain.data import (
    InsightMeshBase, SlackBase,
    InsightMeshUser, Context, Conversation, Message,
    SlackUser, SlackChannel
)

# Database connection
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise ValueError("DB_URL environment variable is required")

# For Slack user lookups, connect to the insight_mesh database on the same server
SLACK_DB_URL = os.getenv("SLACK_DB_URL")
if not SLACK_DB_URL:
    raise ValueError("SLACK_DB_URL environment variable is required")

# Enhanced connection pooling configuration
engine_config = {
    "echo": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600,  # Recycle connections every hour
    "pool_pre_ping": True,  # Validate connections before use
    "connect_args": {
        "server_settings": {
            "application_name": "mcp_server",
        },
        "command_timeout": 30,
    }
}

engine = create_async_engine(DB_URL, **engine_config)
slack_engine = create_async_engine(SLACK_DB_URL, **engine_config)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
slack_async_session = sessionmaker(slack_engine, class_=AsyncSession, expire_on_commit=False)

# Retry decorator for database operations
async def retry_db_operation(operation, max_retries=3, initial_delay=1.0):
    """Retry database operations on connection failures"""
    for attempt in range(max_retries):
        try:
            return await operation()
        except (DisconnectionError, InterfaceError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2 ** attempt)  # Exponential backoff
            await asyncio.sleep(delay)
            continue
        except Exception as e:
            # Don't retry on non-connection errors
            raise e

# Database operations
async def get_user_by_id(user_id: str) -> Optional[InsightMeshUser]:
    """Get our user by ID"""
    async def _operation():
        async with async_session() as session:
            result = await session.execute(
                select(InsightMeshUser).where(InsightMeshUser.id == user_id)
            )
            return result.scalar_one_or_none()
    
    return await retry_db_operation(_operation)

async def get_user_by_email(email: str) -> Optional[InsightMeshUser]:
    """Get our user by email"""
    async def _operation():
        async with async_session() as session:
            result = await session.execute(
                select(InsightMeshUser).where(InsightMeshUser.email == email)
            )
            return result.scalar_one_or_none()
    
    return await retry_db_operation(_operation)

async def create_user(user_id: str, email: str, name: Optional[str] = None, openwebui_id: Optional[str] = None) -> InsightMeshUser:
    """Create a new user in our database"""
    async def _operation():
        async with async_session() as session:
            user = InsightMeshUser(
                id=user_id,
                email=email,
                name=name,
                openwebui_id=openwebui_id,
                is_active=True,
                user_metadata={}
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    return await retry_db_operation(_operation)

async def get_user_contexts(
    user_id: str,
    limit: int = 10,
    active_only: bool = True
) -> List[Context]:
    """Get recent contexts for a user"""
    async def _operation():
        async with async_session() as session:
            query = select(Context).where(Context.user_id == user_id)
            if active_only:
                query = query.where(Context.is_active == True)
            query = query.order_by(Context.created_at.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())
    
    return await retry_db_operation(_operation)

async def create_context(
    user_id: str,
    content: dict,
    expires_at: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Context:
    """Create a new context entry"""
    async def _operation():
        async with async_session() as session:
            context = Context(
                user_id=user_id,
                content=content,
                expires_at=expires_at,
                is_active=True,
                context_metadata=metadata or {}
            )
            session.add(context)
            await session.commit()
            await session.refresh(context)
            return context
    
    return await retry_db_operation(_operation)

async def get_conversation_history(
    user_id: str,
    limit: int = 5,
    active_only: bool = True
) -> List[Conversation]:
    """Get recent conversations for a user"""
    async def _operation():
        async with async_session() as session:
            query = select(Conversation).where(Conversation.user_id == user_id)
            if active_only:
                query = query.where(Conversation.is_active == True)
            query = query.order_by(Conversation.updated_at.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())
    
    return await retry_db_operation(_operation)

async def create_conversation(
    user_id: str,
    title: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Conversation:
    """Create a new conversation"""
    async def _operation():
        async with async_session() as session:
            conversation = Conversation(
                user_id=user_id,
                title=title,
                is_active=True,
                conversation_metadata=metadata or {}
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation
    
    return await retry_db_operation(_operation)

async def add_message(
    conversation_id: int,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> Message:
    """Add a message to a conversation"""
    async def _operation():
        async with async_session() as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_metadata=metadata or {}
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message
    
    return await retry_db_operation(_operation)

async def get_slack_user_by_id(slack_user_id: str) -> Optional[SlackUser]:
    """Get Slack user by ID from insight_mesh database"""
    async def _operation():
        async with slack_async_session() as session:
            result = await session.execute(
                select(SlackUser).where(SlackUser.id == slack_user_id)
            )
            return result.scalar_one_or_none()
    
    return await retry_db_operation(_operation)

async def get_slack_user_by_email(email: str) -> Optional[SlackUser]:
    """Get Slack user by email from insight_mesh database"""
    async def _operation():
        async with slack_async_session() as session:
            result = await session.execute(
                select(SlackUser).where(SlackUser.email == email)
            )
            return result.scalar_one_or_none()
    
    return await retry_db_operation(_operation)

async def init_db():
    """Initialize database tables"""
    async def _operation():
        async with engine.begin() as conn:
            await conn.run_sync(InsightMeshBase.metadata.create_all)
    
    await retry_db_operation(_operation)
    
    # Note: SlackBase tables are managed by the Slack service/migrations
    # We only query them, not create them 