#!/usr/bin/env python3
"""
Domain Composition Architecture Demo

This demonstrates how the new domain layer composes data from multiple sources
to provide business-focused interfaces while keeping the data layer intact for ETL.
"""

import asyncio
from datetime import datetime, timedelta


def show_architecture_overview():
    """Show the new architecture overview."""
    print("Domain Composition Architecture")
    print("=" * 50)
    
    print("\n📊 DATA LAYER (for ETL & raw operations):")
    print("  data/slack/")
    print("    ├── SlackUser      (raw Slack API data)")
    print("    ├── SlackChannel   (raw Slack API data)")
    print("    └── SlackMessage   (raw Slack API data)")
    print("  data/insightmesh/")
    print("    ├── InsightMeshUser (app user data)")
    print("    ├── Conversation   (chat sessions)")
    print("    ├── Message        (conversation messages)")
    print("    └── Context        (user sessions)")
    
    print("\n🏗️ DOMAIN LAYER (for business logic):")
    print("  domain/")
    print("    ├── User           (composes SlackUser + InsightMeshUser)")
    print("    └── Conversation   (composes messages across platforms)")
    
    print("\n🔄 BENEFITS:")
    print("  ✅ ETL jobs use raw data models directly")
    print("  ✅ Business logic uses composed domain objects")
    print("  ✅ Multi-store annotations work on data layer")
    print("  ✅ Cross-platform aggregation in domain layer")


def show_user_composition():
    """Show how User domain object composes multiple sources."""
    print("\n" + "=" * 50)
    print("USER COMPOSITION EXAMPLE")
    print("=" * 50)
    
    print("\n# Find user across all sources by email")
    print("user = await User.from_email('john@company.com', session_factories)")
    print("print(f'Found user: {user.name} from sources: {user.get_loaded_sources()}')")
    print("# Output: Found user: John Doe from sources: ['slack', 'insightmesh']")
    
    print("\n# Access unified business properties")
    print("print(f'Name: {user.name}')           # Best available name")
    print("print(f'Email: {user.email}')         # Best available email") 
    print("print(f'Active: {user.is_active}')    # Active in any system")
    
    print("\n# Check source availability")
    print("if user.has_slack_presence():")
    print("    slack_user = user.get_slack_user()")
    print("    print(f'Slack: {slack_user.display_name_or_name}')")
    print("")
    print("if user.has_insightmesh_account():")
    print("    im_user = user.get_insightmesh_user()")
    print("    print(f'InsightMesh: {im_user.display_name}')")
    
    print("\n# Get comprehensive context")
    print("context = user.get_user_context()")
    print("# Returns unified context from all sources with capabilities")


def show_conversation_composition():
    """Show how Conversation domain object provides business value."""
    print("\n" + "=" * 50)
    print("CONVERSATION COMPOSITION EXAMPLE")
    print("=" * 50)
    
    print("\n# Create conversation from InsightMesh chat session")
    print("im_conversation = session.query(InsightMeshConversation).first()")
    print("conversation = await Conversation.from_insightmesh_conversation(")
    print("    im_conversation, session_factories")
    print(")")
    print("print(f'Conversation: {conversation.identity.title}')")
    print("print(f'Messages: {conversation.message_count}')")
    print("print(f'Participants: {conversation.participant_count}')")
    
    print("\n# Business-focused filtering")
    print("# Get messages from last week")
    print("last_week = datetime.now() - timedelta(days=7)")
    print("recent_messages = conversation.get_messages_by_date_range(")
    print("    last_week, datetime.now()")
    print(")")
    
    print("\n# Get only user messages (exclude AI responses)")
    print("user_messages = conversation.get_user_messages_only()")
    print("print(f'User said {len(user_messages)} things')")
    
    print("\n# Get messages from specific participant")
    print("john_messages = conversation.get_messages_by_participant('user_123')")
    
    print("\n# Cross-platform conversation aggregation")
    print("cross_platform = await Conversation.create_cross_platform_conversation(")
    print("    title='Project Alpha Discussion',")
    print("    participants=['user_123', 'user_456'],")
    print("    topic='alpha',")
    print("    date_range=(last_week, datetime.now()),")
    print("    session_factories=session_factories")
    print(")")
    print("# Finds related messages across Slack, InsightMesh, email")
    
    print("\n# Topic-based conversation discovery")
    print("ai_conversations = await Conversation.find_conversations_by_topic(")
    print("    topic='artificial intelligence',")
    print("    date_range=(last_week, datetime.now()),")
    print("    session_factories=session_factories")
    print(")")
    print("print(f'Found {len(ai_conversations)} AI-related conversations')")


def show_business_use_cases():
    """Show real business use cases enabled by this architecture."""
    print("\n" + "=" * 50)
    print("BUSINESS USE CASES")
    print("=" * 50)
    
    print("\n🎯 USER ANALYTICS:")
    print("  # Find all users active in last 30 days across all platforms")
    print("  # Identify users who have both Slack and InsightMesh presence")
    print("  # Generate user engagement reports across platforms")
    
    print("\n💬 CONVERSATION INTELLIGENCE:")
    print("  # Find all conversations about a specific project")
    print("  # Analyze conversation patterns across platforms")
    print("  # Track topic evolution over time")
    print("  # Identify key participants in discussions")
    
    print("\n📊 CROSS-PLATFORM INSIGHTS:")
    print("  # Correlate Slack discussions with InsightMesh AI usage")
    print("  # Find topics that span multiple communication channels")
    print("  # Identify knowledge gaps (topics discussed but not resolved)")
    
    print("\n🔍 SEARCH & DISCOVERY:")
    print("  # 'Show me all conversations about machine learning last month'")
    print("  # 'Find users who discussed both Python and AI'")
    print("  # 'What topics did John discuss across all platforms?'")
    
    print("\n⚡ REAL-TIME OPERATIONS:")
    print("  # ETL jobs continue to work with raw data models")
    print("  # Business APIs use domain objects for rich functionality")
    print("  # Multi-store sync happens automatically at data layer")


def show_migration_benefits():
    """Show how this preserves existing investments."""
    print("\n" + "=" * 50)
    print("MIGRATION & PRESERVATION BENEFITS")
    print("=" * 50)
    
    print("\n✅ PRESERVED INVESTMENTS:")
    print("  • Existing SQLAlchemy models unchanged")
    print("  • ETL jobs continue working as-is")
    print("  • Multi-store annotations still active")
    print("  • Migration system still works")
    
    print("\n🚀 NEW CAPABILITIES:")
    print("  • Cross-platform user aggregation")
    print("  • Business-focused conversation management")
    print("  • Topic-based discovery across sources")
    print("  • Date/participant filtering")
    print("  • Unified business context")
    
    print("\n🏗️ CLEAN ARCHITECTURE:")
    print("  • data/ = Raw models for ETL")
    print("  • domain/ = Business composition layer")
    print("  • Clear separation of concerns")
    print("  • No redundant schema definitions")


async def main():
    """Run the demonstration."""
    show_architecture_overview()
    show_user_composition()
    show_conversation_composition()
    show_business_use_cases()
    show_migration_benefits()
    
    print("\n" + "=" * 50)
    print("🎉 PERFECT ARCHITECTURE ACHIEVED!")
    print("=" * 50)
    print("✅ ETL jobs use raw data models")
    print("✅ Business logic uses composed domain objects")
    print("✅ Multi-store capabilities preserved")
    print("✅ Cross-platform aggregation enabled")
    print("✅ No schema duplication")
    print("✅ Clean separation of concerns")


if __name__ == "__main__":
    asyncio.run(main()) 