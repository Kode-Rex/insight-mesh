"""
Document Domain Demo - Google Drive and Slack

This example shows how to use the Document domain object that handles
both Google Drive documents and Slack files indexed by the Dagster pipeline.
"""

import asyncio
from domain import (
    Document, DocumentFormat, DocumentSource,
    search_google_docs, search_slack_files, 
    get_recent_google_drive_activity, get_recent_slack_files, get_recent_document_activity
)


async def demo_cross_platform_search():
    """Demonstrate searching across both Google Drive and Slack"""
    
    print("=== Cross-Platform Document Search Demo ===\n")
    
    # 1. Search across both platforms
    print("1. Searching for 'project' across both Google Drive and Slack...")
    try:
        docs = await Document.search_by_content("project", limit=10)
        print(f"Found {len(docs)} documents across both platforms:")
        for doc in docs:
            source_icon = "📄" if doc.source == DocumentSource.GOOGLE_DRIVE else "💬"
            print(f"  {source_icon} {doc.title} ({doc.source.value})")
            print(f"    Format: {doc.identity.format.value}")
            if doc.is_slack_file:
                print(f"    Channel: {doc.identity.channel_id}")
            elif doc.is_google_native:
                print(f"    Google Native: {doc.identity.web_link}")
            print()
    except Exception as e:
        print(f"Error searching documents: {e}\n")
    
    # 2. Search only Google Drive
    print("2. Searching Google Drive only...")
    try:
        google_docs = await Document.search_by_content(
            "meeting", 
            limit=5, 
            sources=[DocumentSource.GOOGLE_DRIVE]
        )
        print(f"Found {len(google_docs)} Google Drive documents:")
        for doc in google_docs:
            print(f"  📄 {doc.title}")
            print(f"    Format: {doc.identity.format.value}")
            print(f"    Size: {doc.size_mb}MB" if doc.size_mb else "    Size: Unknown")
            print()
    except Exception as e:
        print(f"Error searching Google Drive: {e}\n")
    
    # 3. Search only Slack
    print("3. Searching Slack files only...")
    try:
        slack_files = await search_slack_files("document", limit=5)
        print(f"Found {len(slack_files)} Slack files:")
        for doc in slack_files:
            print(f"  💬 {doc.title}")
            print(f"    Channel: {doc.identity.channel_id}")
            print(f"    User: {doc.identity.user_id}")
            print(f"    Format: {doc.identity.format.value}")
            print()
    except Exception as e:
        print(f"Error searching Slack files: {e}\n")


async def demo_recent_activity():
    """Demonstrate getting recent activity from both platforms"""
    
    print("=== Recent Document Activity Demo ===\n")
    
    # 1. Recent activity across both platforms
    print("1. Recent activity across both platforms...")
    try:
        recent_docs = await get_recent_document_activity(days=7)
        print(f"Found {len(recent_docs)} recently active documents:")
        for doc in recent_docs[:5]:  # Show first 5
            source_icon = "📄" if doc.source == DocumentSource.GOOGLE_DRIVE else "💬"
            print(f"  {source_icon} {doc.title}")
            print(f"    Source: {doc.source.value}")
            print(f"    Modified: {doc.identity.modified_date}")
            print()
    except Exception as e:
        print(f"Error getting recent activity: {e}\n")
    
    # 2. Recent Google Drive activity
    print("2. Recent Google Drive activity...")
    try:
        google_recent = await get_recent_google_drive_activity(days=3)
        print(f"Found {len(google_recent)} recent Google Drive documents:")
        for doc in google_recent[:3]:
            print(f"  📄 {doc.title}")
            print(f"    Format: {doc.identity.format.value}")
            print(f"    Modified: {doc.identity.modified_date}")
            print()
    except Exception as e:
        print(f"Error getting Google Drive activity: {e}\n")
    
    # 3. Recent Slack files
    print("3. Recent Slack file activity...")
    try:
        slack_recent = await get_recent_slack_files(days=3)
        print(f"Found {len(slack_recent)} recent Slack files:")
        for doc in slack_recent[:3]:
            print(f"  💬 {doc.title}")
            print(f"    Channel: {doc.identity.channel_id}")
            print(f"    Created: {doc.identity.created_date}")
            print()
    except Exception as e:
        print(f"Error getting Slack file activity: {e}\n")


async def demo_document_retrieval():
    """Demonstrate retrieving specific documents by ID"""
    
    print("=== Document Retrieval Demo ===\n")
    
    # 1. Get Google Drive document by ID
    print("1. Getting Google Drive document by ID...")
    try:
        google_doc = await Document.get_by_file_id("example_google_drive_id", DocumentSource.GOOGLE_DRIVE)
        if google_doc:
            print(f"Google Drive Document: {google_doc.title}")
            print(f"Format: {google_doc.identity.format.value}")
            print(f"Content preview: {google_doc.content[:100]}...")
            print(f"Sharing context: {google_doc.get_sharing_context()}")
        else:
            print("Google Drive document not found (expected for demo)")
        print()
    except Exception as e:
        print(f"Error getting Google Drive document: {e}\n")
    
    # 2. Get Slack file by ID
    print("2. Getting Slack file by ID...")
    try:
        slack_file = await Document.get_by_file_id("example_slack_file_id", DocumentSource.SLACK)
        if slack_file:
            print(f"Slack File: {slack_file.title}")
            print(f"Channel: {slack_file.identity.channel_id}")
            print(f"User: {slack_file.identity.user_id}")
            print(f"Slack metadata: {slack_file.slack_metadata}")
        else:
            print("Slack file not found (expected for demo)")
        print()
    except Exception as e:
        print(f"Error getting Slack file: {e}\n")


async def demo_document_comparison():
    """Demonstrate differences between Google Drive and Slack documents"""
    
    print("=== Document Type Comparison Demo ===\n")
    
    # Create sample documents for comparison
    google_drive_data = {
        'file_id': 'google_doc_123',
        'file_name': 'Project Planning Document',
        'mime_type': 'application/vnd.google-apps.document',
        'content': 'This is a comprehensive project planning document.',
        'web_link': 'https://docs.google.com/document/d/google_doc_123',
        'created_time': '2024-01-15T10:00:00Z',
        'modified_time': '2024-01-20T15:30:00Z',
        'is_public': False,
        'permissions': [
            {'type': 'user', 'role': 'owner', 'email': 'owner@company.com'},
            {'type': 'user', 'role': 'writer', 'email': 'editor@company.com'}
        ]
    }
    
    slack_file_data = {
        'id': 'slack_file_456',
        'name': 'meeting_notes.pdf',
        'mimetype': 'application/pdf',
        'content': 'Meeting notes from the quarterly review.',
        'url_private': 'https://files.slack.com/files-pri/T123/F456/meeting_notes.pdf',
        'size': 1024000,
        'created': '2024-01-18T14:30:00Z',
        'user': 'U789',
        'channels': ['C123'],
        'comments_count': 3,
        'is_external': False,
        'pretty_type': 'PDF'
    }
    
    google_doc = await Document.from_google_drive_data(google_drive_data)
    slack_file = await Document.from_slack_data(slack_file_data)
    
    print("Google Drive Document:")
    print(f"  Title: {google_doc.title}")
    print(f"  Source: {google_doc.source.value}")
    print(f"  Format: {google_doc.identity.format.value}")
    print(f"  Is Google Native: {google_doc.is_google_native}")
    print(f"  Is Text-based: {google_doc.is_text_based}")
    print(f"  Permissions: {len(google_doc.permissions)} entries")
    print(f"  Sharing context: {google_doc.get_sharing_context()}")
    print()
    
    print("Slack File:")
    print(f"  Title: {slack_file.title}")
    print(f"  Source: {slack_file.source.value}")
    print(f"  Format: {slack_file.identity.format.value}")
    print(f"  Is Slack File: {slack_file.is_slack_file}")
    print(f"  Is Text-based: {slack_file.is_text_based}")
    print(f"  Channel: {slack_file.identity.channel_id}")
    print(f"  User: {slack_file.identity.user_id}")
    print(f"  Size: {slack_file.size_mb}MB")
    print(f"  Slack metadata: {slack_file.slack_metadata}")
    print(f"  Sharing context: {slack_file.get_sharing_context()}")
    print()
    
    # Add relationships and show business logic
    google_doc.add_related_conversation("conv_123")
    google_doc.add_related_user("user_456")
    slack_file.add_related_conversation("conv_123")  # Same conversation
    
    print("After adding relationships:")
    print(f"Google Doc sharing context: {google_doc.get_sharing_context()}")
    print(f"Slack File sharing context: {slack_file.get_sharing_context()}")


async def demo_specialized_searches():
    """Demonstrate specialized search functions"""
    
    print("=== Specialized Search Demo ===\n")
    
    # 1. Search specifically for Google Docs
    print("1. Searching specifically for Google Docs...")
    try:
        google_docs = await search_google_docs("planning", limit=3)
        print(f"Found {len(google_docs)} Google Docs:")
        for doc in google_docs:
            print(f"  📄 {doc.title}")
            print(f"    Link: {doc.identity.web_link}")
            print(f"    Native Google Doc: {doc.is_google_native}")
            print()
    except Exception as e:
        print(f"Error searching Google Docs: {e}\n")
    
    # 2. Search specifically for Slack files
    print("2. Searching specifically for Slack files...")
    try:
        slack_files = await search_slack_files("report", limit=3)
        print(f"Found {len(slack_files)} Slack files:")
        for doc in slack_files:
            print(f"  💬 {doc.title}")
            print(f"    Channel: {doc.identity.channel_id}")
            print(f"    Comments: {doc.slack_metadata.get('comments_count', 0)}")
            print()
    except Exception as e:
        print(f"Error searching Slack files: {e}\n")


if __name__ == "__main__":
    print("Document Domain Demo - Google Drive and Slack")
    print("=" * 60)
    print()
    
    # Run all demos
    demos = [
        demo_cross_platform_search,
        demo_recent_activity,
        demo_document_retrieval,
        demo_document_comparison,
        demo_specialized_searches
    ]
    
    for i, demo in enumerate(demos, 1):
        asyncio.run(demo())
        if i < len(demos):
            print("\n" + "=" * 60 + "\n")
    
    print("\nDemo completed!")
    print("\nNote: This demo uses mock data since it requires:")
    print("- Elasticsearch running with indexed Google Drive documents and Slack messages")
    print("- Actual Google Drive files and Slack files indexed by the Dagster pipeline")
    print("- Proper environment variables for Elasticsearch connection")
    print("- Slack messages index with file attachments") 