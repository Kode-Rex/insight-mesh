# Database Migrations

This project uses **standard migration tools** for each database system with **automatic type detection**:

## Migration Tools

### PostgreSQL: Alembic
- **Tool**: [Alembic](https://alembic.sqlalchemy.org/) (industry standard)
- **Type**: `sql`
- **Location**: `.weave/migrations/{database}/`
- **Commands**: `weave db migrate {database}`

### Neo4j: Neo4j Migrations
- **Tool**: [neo4j-migrations](https://github.com/michael-simons/neo4j-migrations) (official)
- **Type**: `graph`
- **Location**: `.weave/migrations/neo4j/cypher/`
- **Commands**: `weave db migrate neo4j`

### Elasticsearch: HTTP-based Migrations
- **Tool**: HTTP requests (compatible with [elasticsearch-evolution](https://github.com/senacor/elasticsearch-evolution))
- **Type**: `search`
- **Location**: `.weave/migrations/elasticsearch/scripts/`
- **Commands**: `weave db migrate elasticsearch`

## Quick Start

### Smart Migration (Recommended)
The system automatically detects database types and uses the appropriate migration tool:

```bash
# Show all configured databases and their types
weave db info

# Migrate any database (auto-detects type and tool)
weave db migrate slack          # Uses Alembic (SQL)
weave db migrate neo4j          # Uses neo4j-migrations (Graph)
weave db migrate elasticsearch  # Uses HTTP-based (Search)

# Migrate all databases
weave db migrate all
```

### Run All Migrations by Type
```bash
# Migrate all database systems
weave db migrate-all

# Migrate specific types only
weave db migrate-all --no-include-sql      # Skip PostgreSQL
weave db migrate-all --no-include-graph    # Skip Neo4j
weave db migrate-all --no-include-search   # Skip Elasticsearch
```

### Individual Database Migrations

#### PostgreSQL (Alembic) - Type: `sql`
```bash
# Create new migration
weave db create slack "add user preferences"
weave db create insightmesh "add context metadata"

# Apply migrations (smart command)
weave db migrate slack
weave db migrate insightmesh

# Show current state
weave db current slack
weave db history slack
```

#### Neo4j (neo4j-migrations) - Type: `graph`
```bash
# Apply migrations (smart command)
weave db migrate neo4j

# Direct neo4j-migrations commands
weave db migrate-neo4j migrate
weave db migrate-neo4j info
weave db migrate-neo4j validate
weave db migrate-neo4j clean
```

#### Elasticsearch (HTTP-based) - Type: `search`
```bash
# Apply migrations (smart command)
weave db migrate elasticsearch

# Direct elasticsearch commands
weave db migrate-elasticsearch migrate
weave db migrate-elasticsearch info
```

## Database Configuration

Databases are configured in `.weave/config.json` with type information:

```json
{
  "databases": {
    "slack": {
      "type": "sql",
      "migration_tool": "alembic",
      "description": "Slack integration data"
    },
    "neo4j": {
      "type": "graph", 
      "migration_tool": "neo4j-migrations",
      "description": "Knowledge graph database"
    },
    "elasticsearch": {
      "type": "search",
      "migration_tool": "elasticsearch-evolution", 
      "description": "Search and analytics engine"
    }
  }
}
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

## Command Reference

### Smart Commands (Recommended)
```bash
weave db info                    # Show all databases and types
weave db migrate <database>      # Smart migrate (auto-detects tool)
weave db migrate all             # Migrate all databases
weave db migrate-all             # Migrate all with type filtering
```

### Type-Specific Commands
```bash
# SQL databases (PostgreSQL + Alembic)
weave db create <database> <message>     # Create migration
weave db migrate <database>              # Apply migrations
weave db current <database>              # Show current revision
weave db history <database>              # Show migration history

# Graph databases (Neo4j + neo4j-migrations)
weave db migrate-neo4j migrate           # Apply migrations
weave db migrate-neo4j info              # Show migration info
weave db migrate-neo4j validate          # Validate migrations
weave db migrate-neo4j clean             # Clean database

# Search databases (Elasticsearch + HTTP)
weave db migrate-elasticsearch migrate   # Apply migrations
weave db migrate-elasticsearch info      # Show current indices
```

## Installation Requirements

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Neo4j Migrations CLI (Java required)
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
docker-compose --profile migrations run migrations weave db migrate all
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
1. **Use smart commands** - `weave db migrate <database>` auto-detects the right tool
2. **Check database info** - `weave db info` shows all databases and their types
3. **Always backup** before running migrations in production
4. **Test migrations** in development first
5. **Version control** all migration files

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

### Check Database Configuration
```bash
# Show all databases with types and tools
weave db info
```

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

## Migration Flow

1. **Configure** databases in `.weave/config.json` with correct types
2. **Create** migrations using appropriate tools/formats
3. **Apply** migrations using smart commands: `weave db migrate <database>`
4. **Verify** using `weave db info` and type-specific status commands

The system automatically routes to the correct migration tool based on the database type configuration! 