"""
Example usage of multi-store SQLAlchemy models.

This demonstrates how to use existing SQLAlchemy models enhanced with
Neo4j and Elasticsearch capabilities through Weave annotations.

The annotations integrate seamlessly with the existing migration system.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.data.slack import SlackUser, SlackChannel, SlackBase
from weave.bin.modules.annotations.sync import bulk_sync_to_stores


def setup_example():
    """Set up example database and data."""
    # Use your existing database connection
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/slack")
    Session = sessionmaker(bind=engine)
    
    return Session()


def example_seamless_workflow():
    """
    Example of the seamless workflow:
    
    1. Add annotations to your existing SQLAlchemy models
    2. Run: weave migrate create slack "add search and graph capabilities" --autogenerate
    3. Run: weave migrate up
    4. Your models now have multi-store capabilities!
    """
    
    print("=== Seamless Multi-Store Workflow ===")
    print()
    print("1. Add annotations to your existing models:")
    print("""
    @neo4j_node(label="SlackUser")
    @elasticsearch_index(index_name="slack_users", text_fields=['name'])
    class SlackUser(SlackBase):
        # Your existing SQLAlchemy model - unchanged!
        __tablename__ = 'slack_users'
        # ... existing fields
    """)
    
    print("2. Run autogenerate migration:")
    print("   weave migrate create slack 'add search and graph capabilities' --autogenerate")
    print("   → Detects annotation changes")
    print("   → Creates Neo4j migration")
    print("   → Creates Elasticsearch migration") 
    print("   → Creates SQLAlchemy migration (if needed)")
    print()
    
    print("3. Apply migrations:")
    print("   weave migrate up")
    print("   → Applies all migrations across all systems")
    print()
    
    print("4. Use enhanced models:")
    session = setup_example()
    
    # Create a user - automatically syncs to all stores
    user = SlackUser(
        id="U123456",
        name="john.doe",
        real_name="John Doe",
        display_name="John",
        email="john.doe@company.com",
        is_admin=False,
        is_bot=False,
        deleted=False,
        team_id="T123456"
    )
    
    session.add(user)
    session.commit()  # Auto-syncs to Neo4j and Elasticsearch
    
    print(f"   ✅ Created user: {user.display_name_or_name}")
    print("   → Automatically synced to PostgreSQL, Neo4j, and Elasticsearch")
    
    session.close()


def example_search_capabilities():
    """Example of the search capabilities added by annotations."""
    print("\n=== Search Capabilities ===")
    
    # These methods are automatically added by the annotations
    print("Elasticsearch full-text search:")
    print("   results = SlackUser.search_elasticsearch('John Doe')")
    
    print("\nNeo4j graph queries:")
    print("   admins = SlackUser.find_in_neo4j(is_admin=True)")
    
    print("\nManual sync (if needed):")
    print("   user.sync_to_neo4j()")
    print("   user.sync_to_elasticsearch()")
    print("   user.sync_all_stores()")


def example_migration_detection():
    """Example of what the migration system detects."""
    print("\n=== Migration Detection ===")
    print("The system automatically detects when you:")
    print("  ✅ Add @neo4j_node to a model → Creates Neo4j constraints")
    print("  ✅ Add @elasticsearch_index → Creates ES index with mapping")
    print("  ✅ Add @neo4j_relationship → Sets up graph relationships")
    print("  ✅ Change annotation config → Updates schemas accordingly")
    print("  ✅ Remove annotations → Cleans up schemas")
    print()
    print("All integrated into your existing 'weave migrate' workflow!")


if __name__ == "__main__":
    example_seamless_workflow()
    example_search_capabilities()
    example_migration_detection()
    
    print("\n🎉 Multi-store capabilities added with zero ORM reinvention!") 