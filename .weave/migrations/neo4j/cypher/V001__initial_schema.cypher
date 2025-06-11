// V001__initial_schema.cypher
// Initial Neo4j schema setup - constraints, indexes, and base data

// Create constraints for unique identifiers
CREATE CONSTRAINT file_id IF NOT EXISTS
FOR (f:File) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT owner_email IF NOT EXISTS
FOR (o:Owner) REQUIRE o.email IS UNIQUE;

CREATE CONSTRAINT folder_id IF NOT EXISTS
FOR (f:Folder) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT slack_channel_id IF NOT EXISTS
FOR (c:SlackChannel) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT slack_user_id IF NOT EXISTS
FOR (u:SlackUser) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT slack_message_id IF NOT EXISTS
FOR (m:SlackMessage) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT web_page_url IF NOT EXISTS
FOR (p:WebPage) REQUIRE p.url IS UNIQUE;

// Create indexes for better query performance
CREATE INDEX file_name IF NOT EXISTS
FOR (f:File) ON (f.name);

CREATE INDEX owner_name IF NOT EXISTS
FOR (o:Owner) ON (o.displayName);

CREATE INDEX slack_channel_name IF NOT EXISTS
FOR (c:SlackChannel) ON (c.name);

CREATE INDEX slack_user_name IF NOT EXISTS
FOR (u:SlackUser) ON (u.name);

CREATE INDEX web_page_title IF NOT EXISTS
FOR (p:WebPage) ON (p.title);

// Create full-text indexes for content search
CREATE FULLTEXT INDEX file_content IF NOT EXISTS
FOR (f:File) ON EACH [f.name, f.content];

CREATE FULLTEXT INDEX slack_message_content IF NOT EXISTS
FOR (m:SlackMessage) ON EACH [m.text];

CREATE FULLTEXT INDEX web_page_content IF NOT EXISTS
FOR (p:WebPage) ON EACH [p.title, p.content];

// Create relationship indexes
CREATE INDEX relationship_types IF NOT EXISTS
FOR ()-[r]-() ON (type(r));

CREATE INDEX similarity_score IF NOT EXISTS
FOR ()-[r:SIMILAR_TO]-() ON (r.score);

CREATE INDEX shared_permissions IF NOT EXISTS
FOR ()-[r:SHARED_WITH]-() ON (r.permission);

// Create metadata for the graph
CREATE (meta:Metadata {
    version: '1.0',
    created_at: datetime(),
    description: 'InsightMesh knowledge graph schema',
    schema_version: 'V001'
});

// Create initial folder structure
MERGE (root:Folder {id: 'root', name: 'Root'})
WITH root
MATCH (meta:Metadata)
MERGE (meta)-[:DESCRIBES]->(root);

// Create common file types as categories
MERGE (doc:FileType {name: 'Document', mime_types: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']})
MERGE (sheet:FileType {name: 'Spreadsheet', mime_types: ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']})
MERGE (slide:FileType {name: 'Presentation', mime_types: ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']})
MERGE (image:FileType {name: 'Image', mime_types: ['image/jpeg', 'image/png', 'image/gif', 'image/webp']})
MERGE (text:FileType {name: 'Text', mime_types: ['text/plain', 'text/markdown', 'text/html']})
MERGE (other:FileType {name: 'Other', mime_types: []});

// Create relationship types metadata
CREATE (rt:RelationshipTypes {
    types: [
        'OWNED_BY',
        'IN_FOLDER', 
        'CONTAINS',
        'SIMILAR_TO',
        'RELATED_TO',
        'VERSION_OF',
        'SHARED_WITH',
        'LINKS_TO',
        'HAS_PIN',
        'HAS_BOOKMARK',
        'IS_MEMBER_OF',
        'REACTED_WITH',
        'CONTAINS_IMAGE'
    ],
    created_at: datetime()
}); 