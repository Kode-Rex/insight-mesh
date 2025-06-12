# Multi-Store Annotations for SQLAlchemy Models

This annotation system allows you to enhance existing SQLAlchemy models with Neo4j graph and Elasticsearch search capabilities without duplicating schema definitions or reinventing ORM functionality.

## Philosophy

Instead of creating separate domain models that duplicate your SQLAlchemy schema, this system:

1. **Leverages existing SQLAlchemy models** as the single source of truth
2. **Adds capabilities through decorators** for Neo4j and Elasticsearch
3. **Maintains your existing migrations** and database structure
4. **Provides automatic synchronization** across all stores

## Quick Start

### 1. Annotate Your Existing Models

```python
from domain.annotations import neo4j_node, elasticsearch_index, neo4j_relationship

@neo4j_node(
    label="SlackUser",
    exclude_fields=['data']
)
@elasticsearch_index(
    index_name="slack_users",
    text_fields=['name']
)
class SlackUser(SlackBase):
    # Your existing SQLAlchemy model definition
    __tablename__ = 'slack_users'
    id = Column(String(255), primary_key=True)
    # ... rest of your model
```

### 2. Enable Auto-Sync

```python
from domain.annotations.sync import enable_auto_sync_for_model

enable_auto_sync_for_model(SlackUser)
```

### 3. Use Normally

```python
# Create/update/delete as usual - sync happens automatically
user = SlackUser(id="U123", name="john")
session.add(user)
session.commit()  # Auto-syncs to Neo4j and Elasticsearch
```

## Available Decorators

### `@neo4j_node`

Marks a SQLAlchemy model as a Neo4j node.

```python
@neo4j_node(
    label="NodeLabel",           # Neo4j node label
    properties=None,             # Fields to sync (None = all)
    id_field='id',              # Primary key field
    exclude_fields=['field1']    # Fields to exclude
)
```

### `@neo4j_relationship`

Defines relationships between models.

```python
@neo4j_relationship(
    type="CREATED_BY",          # Relationship type
    target_model=SlackUser,     # Target model class
    source_field="creator",     # Field containing target ID
    target_field="id"           # Target model's ID field
)
```

### `@elasticsearch_index`

Marks a model for Elasticsearch indexing.

```python
@elasticsearch_index(
    index_name="my_index",      # Elasticsearch index name
    text_fields=['name'],       # Fields for full-text search
    exclude_fields=['data'],    # Fields to exclude
    mapping=None                # Custom ES mapping (optional)
)
```

## Capabilities Added to Models

Once annotated, your models gain these methods:

### Neo4j Methods
- `sync_to_neo4j()` - Sync instance to Neo4j
- `sync_relationships_to_neo4j()` - Sync relationships
- `find_in_neo4j(**filters)` - Search Neo4j nodes
- `get_neo4j_driver()` - Get Neo4j driver

### Elasticsearch Methods
- `sync_to_elasticsearch()` - Sync instance to Elasticsearch
- `delete_from_elasticsearch()` - Remove from Elasticsearch
- `search_elasticsearch(query)` - Search in Elasticsearch
- `create_elasticsearch_index()` - Create index with mapping

### Sync Methods
- `sync_all_stores()` - Sync to all configured stores
- `enable_auto_sync()` - Enable automatic sync on changes

## Synchronization Options

### Automatic Sync (Recommended)

```python
from domain.annotations.sync import enable_auto_sync_for_model

enable_auto_sync_for_model(MyModel)

# Now all changes automatically sync
user = MyModel(...)
session.add(user)
session.commit()  # Auto-syncs to Neo4j and Elasticsearch
```

### Manual Sync

```python
user = session.query(SlackUser).first()
user.sync_all_stores()  # Sync to all stores

# Or sync to specific stores
user.sync_to_neo4j()
user.sync_to_elasticsearch()
```

### Bulk Sync (for existing data)

```python
from domain.annotations.sync import bulk_sync_to_stores

# Sync all users
bulk_sync_to_stores(session, SlackUser)

# Sync with filters
bulk_sync_to_stores(session, SlackUser, is_active=True)
```

## Benefits

1. **No Schema Duplication** - SQLAlchemy remains the single source of truth
2. **Leverage Existing Migrations** - Your Alembic migrations continue to work
3. **Gradual Adoption** - Add annotations to models as needed
4. **Automatic Sync** - Changes propagate automatically across stores
5. **Flexible Configuration** - Control what gets synced where
6. **Business Logic Preserved** - Add domain methods to your models as usual

## Integration with Existing Code

This system works with your existing:
- ✅ SQLAlchemy models and relationships
- ✅ Alembic migrations
- ✅ Database connections and sessions
- ✅ Business logic and domain methods
- ✅ Existing services and DAOs

## Example: Complete Model Enhancement

```python
@neo4j_node(
    label="SlackUser",
    exclude_fields=['data', 'created_at', 'updated_at']
)
@neo4j_relationship(
    type="MEMBER_OF",
    target_model=SlackChannel,
    source_field="team_id"
)
@elasticsearch_index(
    index_name="slack_users",
    text_fields=['name', 'real_name', 'display_name'],
    exclude_fields=['data']
)
class SlackUser(SlackBase):
    # Your existing SQLAlchemy definition
    __tablename__ = 'slack_users'
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    # ... existing fields
    
    # Your existing business logic
    def is_active_user(self):
        return not self.deleted and not self.is_bot
    
    # Now also has Neo4j and Elasticsearch capabilities!
```

This approach lets you keep your existing ORM investment while adding powerful graph and search capabilities. 