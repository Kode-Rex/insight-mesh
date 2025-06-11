"""Initial Neo4j constraints and indexes

Migration ID: neo4j_001
Created: 2024-01-20 12:00:00.000000
Description: Create initial constraints, indexes, and metadata for Neo4j graph database
"""

def upgrade(session):
    """Apply the migration - create constraints, indexes, and initial data."""
    
    # Create constraints for unique identifiers
    session.run("""
        CREATE CONSTRAINT file_id IF NOT EXISTS
        FOR (f:File) REQUIRE f.id IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT owner_email IF NOT EXISTS
        FOR (o:Owner) REQUIRE o.email IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT folder_id IF NOT EXISTS
        FOR (f:Folder) REQUIRE f.id IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT slack_channel_id IF NOT EXISTS
        FOR (c:SlackChannel) REQUIRE c.id IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT slack_user_id IF NOT EXISTS
        FOR (u:SlackUser) REQUIRE u.id IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT slack_message_id IF NOT EXISTS
        FOR (m:SlackMessage) REQUIRE m.id IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT web_page_url IF NOT EXISTS
        FOR (p:WebPage) REQUIRE p.url IS UNIQUE
    """)
    
    session.run("""
        CREATE CONSTRAINT web_image_url IF NOT EXISTS
        FOR (i:WebImage) REQUIRE i.url IS UNIQUE
    """)
    
    # Create indexes for better query performance
    session.run("""
        CREATE INDEX file_name IF NOT EXISTS
        FOR (f:File) ON (f.name)
    """)
    
    session.run("""
        CREATE INDEX owner_name IF NOT EXISTS
        FOR (o:Owner) ON (o.displayName)
    """)
    
    session.run("""
        CREATE INDEX slack_channel_name IF NOT EXISTS
        FOR (c:SlackChannel) ON (c.name)
    """)
    
    session.run("""
        CREATE INDEX slack_user_name IF NOT EXISTS
        FOR (u:SlackUser) ON (u.name)
    """)
    
    session.run("""
        CREATE INDEX web_page_title IF NOT EXISTS
        FOR (p:WebPage) ON (p.title)
    """)
    
    # Create full-text indexes for content search
    session.run("""
        CREATE FULLTEXT INDEX file_content IF NOT EXISTS
        FOR (f:File) ON EACH [f.name, f.content]
    """)
    
    session.run("""
        CREATE FULLTEXT INDEX slack_message_content IF NOT EXISTS
        FOR (m:SlackMessage) ON EACH [m.text]
    """)
    
    session.run("""
        CREATE FULLTEXT INDEX web_page_content IF NOT EXISTS
        FOR (p:WebPage) ON EACH [p.title, p.content]
    """)
    
    # Create relationship indexes
    session.run("""
        CREATE INDEX relationship_types IF NOT EXISTS
        FOR ()-[r]-() ON (type(r))
    """)
    
    session.run("""
        CREATE INDEX similarity_score IF NOT EXISTS
        FOR ()-[r:SIMILAR_TO]-() ON (r.score)
    """)
    
    session.run("""
        CREATE INDEX shared_permissions IF NOT EXISTS
        FOR ()-[r:SHARED_WITH]-() ON (r.permission)
    """)
    
    # Create metadata for the graph
    session.run("""
        CREATE (meta:Metadata {
            version: '1.0',
            last_updated: datetime(),
            description: 'InsightMesh graph database for documents, relationships, and metadata'
        })
    """)
    
    # Create initial folder structure
    session.run("""
        MERGE (root:Folder {id: 'root', name: 'Root'})
        WITH root
        MATCH (meta:Metadata)
        MERGE (meta)-[:DESCRIBES]->(root)
    """)
    
    # Create common file types as categories
    session.run("""
        MERGE (doc:FileType {name: 'Document'})
        MERGE (sheet:FileType {name: 'Spreadsheet'})
        MERGE (slide:FileType {name: 'Presentation'})
        MERGE (image:FileType {name: 'Image'})
        MERGE (pdf:FileType {name: 'PDF'})
        MERGE (other:FileType {name: 'Other'})
    """)
    
    # Create relationship types metadata
    session.run("""
        CREATE (rt:RelationshipTypes {
            types: [
                'OWNED_BY',
                'IN_FOLDER',
                'SIMILAR_TO',
                'RELATED_TO',
                'VERSION_OF',
                'SHARED_WITH',
                'CONTAINS',
                'LINKS_TO',
                'HAS_PIN',
                'HAS_BOOKMARK',
                'IS_MEMBER_OF',
                'REACTED_WITH',
                'CONTAINS_IMAGE'
            ]
        })
    """)

def downgrade(session):
    """Revert the migration - remove constraints, indexes, and initial data."""
    
    # Remove relationship types metadata
    session.run("MATCH (rt:RelationshipTypes) DELETE rt")
    
    # Remove file types
    session.run("MATCH (ft:FileType) DELETE ft")
    
    # Remove metadata and relationships
    session.run("MATCH (meta:Metadata)-[r]-() DELETE r, meta")
    
    # Remove root folder
    session.run("MATCH (root:Folder {id: 'root'}) DELETE root")
    
    # Drop indexes (Neo4j will automatically drop them when constraints are dropped)
    session.run("DROP INDEX shared_permissions IF EXISTS")
    session.run("DROP INDEX similarity_score IF EXISTS")
    session.run("DROP INDEX relationship_types IF EXISTS")
    session.run("DROP FULLTEXT INDEX web_page_content IF EXISTS")
    session.run("DROP FULLTEXT INDEX slack_message_content IF EXISTS")
    session.run("DROP FULLTEXT INDEX file_content IF EXISTS")
    session.run("DROP INDEX web_page_title IF EXISTS")
    session.run("DROP INDEX slack_user_name IF EXISTS")
    session.run("DROP INDEX slack_channel_name IF EXISTS")
    session.run("DROP INDEX owner_name IF EXISTS")
    session.run("DROP INDEX file_name IF EXISTS")
    
    # Drop constraints
    session.run("DROP CONSTRAINT web_image_url IF EXISTS")
    session.run("DROP CONSTRAINT web_page_url IF EXISTS")
    session.run("DROP CONSTRAINT slack_message_id IF EXISTS")
    session.run("DROP CONSTRAINT slack_user_id IF EXISTS")
    session.run("DROP CONSTRAINT slack_channel_id IF EXISTS")
    session.run("DROP CONSTRAINT folder_id IF EXISTS")
    session.run("DROP CONSTRAINT owner_email IF EXISTS")
    session.run("DROP CONSTRAINT file_id IF EXISTS") 