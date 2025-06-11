# Database Migrations

This project uses **standard migration tools** for each database system:

## Migration Tools

### PostgreSQL: Alembic
- **Tool**: [Alembic](https://alembic.sqlalchemy.org/) (industry standard)
- **Location**: `.weave/migrations/{database}/`
- **Commands**: `weave db migrate {database}`, `weave db create {database}`

### Neo4j: Neo4j Migrations
- **Tool**: [neo4j-migrations](https://github.com/michael-simons/neo4j-migrations) (official)
- **Location**: `.weave/migrations/neo4j/cypher/`
- **Commands**: `weave db migrate-neo4j`

### Elasticsearch: HTTP-based Migrations
- **Tool**: HTTP requests (compatible with [elasticsearch-evolution](https://github.com/senacor/elasticsearch-evolution))
- **Location**: `.weave/migrations/elasticsearch/scripts/`
- **Commands**: `weave db migrate-elasticsearch`

## Quick Start

### Run All Migrations
```bash
# Migrate all database systems
weave db migrate-all

# Migrate specific systems only
weave db migrate-all --no-include-postgres
weave db migrate-all --no-include-neo4j
weave db migrate-all --no-include-elasticsearch
```

### Individual Database Migrations

#### PostgreSQL (Alembic)
```bash
# Create new migration
weave db create slack "add user preferences"
weave db create insightmesh "add context metadata"

# Apply migrations
weave db migrate slack
weave db migrate insightmesh

# Show current state
weave db current slack
weave db history slack
```

#### Neo4j (neo4j-migrations)
```bash
# Apply migrations
weave db migrate-neo4j migrate

# Show migration info
weave db migrate-neo4j info

# Validate migrations
weave db migrate-neo4j validate

# Clean database (removes all data!)
weave db migrate-neo4j clean
```

#### Elasticsearch (HTTP-based)
```bash
# Apply index migrations
weave db migrate-elasticsearch migrate

# Show current indices
weave db migrate-elasticsearch info
```

## Creating New Migrations

### PostgreSQL Migrations
```bash
# Auto-generate from model changes
weave db create slack "add new table" --auto

# Create empty migration
weave db create insightmesh "custom changes"
```

### Neo4j Migrations
Create a new file in `.weave/migrations/neo4j/cypher/`:
```cypher
// V002__add_user_relationships.cypher
// Add user relationship constraints and indexes

CREATE CONSTRAINT user_id IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE INDEX user_email IF NOT EXISTS
FOR (u:User) ON (u.email);
```

### Elasticsearch Migrations
Create a new file in `.weave/migrations/elasticsearch/scripts/`:
```http
# V002__add_user_index.http
# Add user index for authentication

### Create users index
PUT /users
Content-Type: application/json

{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "email": { "type": "keyword" },
      "name": { "type": "text" },
      "created_at": { "type": "date" }
    }
  }
}
```

## Migration File Naming

### Neo4j (Cypher)
- Format: `V{version}__{description}.cypher`
- Example: `V001__initial_schema.cypher`

### Elasticsearch (HTTP)
- Format: `V{version}__{description}.http`
- Example: `V001__initial_indices.http`

### PostgreSQL (Alembic)
- Auto-generated: `{revision}_{description}.py`
- Example: `abc123_add_user_table.py`

## Installation Requirements

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Neo4j Migrations CLI (Java required)
# Download from: https://github.com/michael-simons/neo4j-migrations/releases
wget https://github.com/michael-simons/neo4j-migrations/releases/download/1.16.0/neo4j-migrations-1.16.0.zip
unzip neo4j-migrations-1.16.0.zip
sudo mv neo4j-migrations-1.16.0 /opt/neo4j-migrations
sudo ln -s /opt/neo4j-migrations/bin/neo4j-migrations /usr/local/bin/neo4j-migrations
```

### Docker
```bash
# Build migration service (includes all tools)
docker-compose build migrations

# Run migrations in Docker
docker-compose --profile migrations run migrations weave db migrate-all
```

## Environment Variables

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_SCHEME=http
```

## Best Practices

### General
1. **Always backup** before running migrations in production
2. **Test migrations** in development first
3. **Version control** all migration files
4. **Never edit** applied migration files

### Neo4j Specific
1. Use `IF NOT EXISTS` for constraints and indexes
2. Use `MERGE` instead of `CREATE` for idempotent operations
3. Keep migrations atomic and reversible when possible

### Elasticsearch Specific
1. Use index templates for consistent settings
2. Consider index aliases for zero-downtime updates
3. Test mapping changes carefully (they're often irreversible)

### PostgreSQL Specific
1. Use Alembic's autogenerate feature
2. Review generated migrations before applying
3. Add custom data migrations when needed

## Troubleshooting

### Neo4j Migrations
```bash
# Check if Neo4j is accessible
neo4j-migrations info -c .weave/migrations/neo4j/neo4j.conf

# Validate migration files
neo4j-migrations validate -c .weave/migrations/neo4j/neo4j.conf
```

### Elasticsearch Migrations
```bash
# Check Elasticsearch connectivity
curl http://localhost:9200/_cluster/health

# List current indices
curl http://localhost:9200/_cat/indices?v
```

### PostgreSQL Migrations
```bash
# Check current revision
weave db current slack

# Show migration history
weave db history slack
``` 