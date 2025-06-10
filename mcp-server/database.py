from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func, select
from typing import Optional, List
import os
from datetime import datetime

# Import domain models instead of defining our own
from domain import (
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

engine = create_async_engine(DB_URL, echo=True)
slack_engine = create_async_engine(SLACK_DB_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
slack_async_session = sessionmaker(slack_engine, class_=AsyncSession, expire_on_commit=False)

# Database operations
async def get_user_by_id(user_id: str) -> Optional[InsightMeshUser]:
    """Get our user by ID"""
    async with async_session() as session:
        result = await session.execute(
            select(InsightMeshUser).where(InsightMeshUser.id == user_id)
        )
        return result.scalar_one_or_none()

async def get_user_by_email(email: str) -> Optional[InsightMeshUser]:
    """Get our user by email"""
    async with async_session() as session:
        result = await session.execute(
            select(InsightMeshUser).where(InsightMeshUser.email == email)
        )
        return result.scalar_one_or_none()

async def create_user(user_id: str, email: str, name: Optional[str] = None, openwebui_id: Optional[str] = None) -> InsightMeshUser:
    """Create a new user in our database"""
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

async def get_user_contexts(
    user_id: str,
    limit: int = 10,
    active_only: bool = True
) -> List[Context]:
    """Get recent contexts for a user"""
    async with async_session() as session:
        query = select(Context).where(Context.user_id == user_id)
        if active_only:
            query = query.where(Context.is_active == True)
        query = query.order_by(Context.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

async def create_context(
    user_id: str,
    content: dict,
    expires_at: Optional[datetime] = None,
    metadata: Optional[dict] = None
) -> Context:
    """Create a new context entry"""
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

async def get_conversation_history(
    user_id: str,
    limit: int = 5,
    active_only: bool = True
) -> List[Conversation]:
    """Get recent conversations for a user"""
    async with async_session() as session:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if active_only:
            query = query.where(Conversation.is_active == True)
        query = query.order_by(Conversation.updated_at.desc()).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

async def create_conversation(
    user_id: str,
    title: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Conversation:
    """Create a new conversation"""
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

async def add_message(
    conversation_id: int,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> Message:
    """Add a message to a conversation"""
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

async def get_slack_user_by_id(slack_user_id: str) -> Optional[SlackUser]:
    """Get Slack user by ID from insight_mesh database"""
    async with slack_async_session() as session:
        result = await session.execute(
            select(SlackUser).where(SlackUser.id == slack_user_id)
        )
        return result.scalar_one_or_none()

async def get_slack_user_by_email(email: str) -> Optional[SlackUser]:
    """Get Slack user by email from insight_mesh database"""
    async with slack_async_session() as session:
        result = await session.execute(
            select(SlackUser).where(SlackUser.email == email)
        )
        return result.scalar_one_or_none()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(InsightMeshBase.metadata.create_all)
    
    # Note: SlackBase tables are managed by the Slack service/migrations
    # We only query them, not create them 