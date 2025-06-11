# Weave Multi-Store Annotations

## Overview

We've successfully integrated a powerful multi-store annotation system into the Weave CLI that enhances existing SQLAlchemy models with Neo4j graph and Elasticsearch search capabilities. The system seamlessly integrates with the existing migration workflow, automatically detecting annotation changes and generating appropriate migrations across all systems.

## What We Built

### 1. Annotation System (`weave/bin/modules/annotations/`)

**Core Components:**
- `graph.py` - Neo4j node and relationship decorators + GraphMixin
- `search.py` - Elasticsearch indexing decorators + SearchMixin  
- `sync.py` - Automatic synchronization utilities + SyncMixin
- `__init__.py` - Clean API exports

**Key Features:**
- **`@neo4j_node`** - Marks SQLAlchemy models as Neo4j nodes
- **`@neo4j_relationship`** - Defines graph relationships between models
- **`@elasticsearch_index`** - Enables full-text search indexing
- **Auto-sync** - SQLAlchemy events automatically propagate changes
- **Migration detection** - Changes automatically detected and migrated

### 2. Enhanced Domain Models

**Updated Models:**
- `domain/data/slack/user.py` - SlackUser with Neo4j + Elasticsearch
- `domain/data/slack/channel.py` - SlackChannel with relationships
- `domain/data/slack/__init__.py` - Auto-sync enabled

**Example Enhancement:**
```python
@neo4j_node(label="SlackUser", exclude_fields=['data'])
@elasticsearch_index(index_name="slack_users", text_fields=['name'])
class SlackUser(SlackBase):
    # Existing SQLAlchemy definition unchanged
    __tablename__ = 'slack_users'
    id = Column(String(255), primary_key=True)
    # ... rest of model
    
    # Business logic preserved
    def is_active_user(self):
        return not self.deleted and not self.is_bot
```

### 3. Seamless Migration Integration

**Enhanced Migration Detection:**
- `annotation_migration_detector.py` - Detects annotation changes
- Enhanced `weave migrate create --autogenerate` - Now detects both SQLAlchemy and annotation changes
- Automatic generation of Neo4j and Elasticsearch migrations

**Workflow:**
```bash
# 1. Add annotations to your models
# 2. Run autogenerate migration
weave migrate create slack "add search and graph capabilities" --autogenerate

# This now automatically:
# → Detects annotation changes
# → Creates Neo4j migration
# → Creates Elasticsearch migration  
# → Creates SQLAlchemy migration (if needed)

# 3. Apply all migrations
weave migrate up
```

### 4. Documentation & Examples

**Files Created:**
- `weave/bin/modules/annotations/README.md` - Comprehensive documentation
- `examples/multi_store_usage.py` - Seamless workflow examples
- `tests/test_annotations.py` - Test suite
- `annotation_migration_detector.py` - Migration detection system

## Architecture Benefits

### ✅ **Seamless Integration**
- No separate annotation management commands needed
- Integrates with existing `weave migrate` workflow
- Automatic detection of annotation changes
- Single command creates migrations across all systems

### ✅ **Leverages Existing Investment**
- SQLAlchemy models remain the single source of truth
- Alembic migrations continue to work unchanged
- Database connections and sessions work as before
- Business logic methods are preserved

### ✅ **No Schema Duplication**
- One model definition serves all stores
- Annotations control what gets synced where
- Flexible field inclusion/exclusion
- Automatic type mapping

### ✅ **Multi-Store Capabilities**
- **PostgreSQL** - Primary relational data (via SQLAlchemy)
- **Neo4j** - Graph relationships and traversals
- **Elasticsearch** - Full-text search and analytics
- **Automatic sync** - Changes propagate across all stores

## Seamless Workflow

### 1. Add Annotations
```python
@neo4j_node(label="SlackUser")
@elasticsearch_index(index_name="slack_users", text_fields=['name'])
class SlackUser(SlackBase):
    # Your existing SQLAlchemy model - unchanged!
```

### 2. Generate Migrations
```bash
weave migrate create slack "add search and graph capabilities" --autogenerate
```
**Automatically detects and creates:**
- Neo4j constraints and indexes
- Elasticsearch index mappings
- SQLAlchemy schema changes (if any)

### 3. Apply Migrations
```bash
weave migrate up
```
**Applies migrations across all systems**

### 4. Use Enhanced Models
```python
# Create/update as usual - sync happens automatically
user = SlackUser(id="U123", name="john", email="john@company.com")
session.add(user)
session.commit()  # Auto-syncs to Neo4j and Elasticsearch

# New capabilities automatically available
results = SlackUser.search_elasticsearch("John Doe")
admins = SlackUser.find_in_neo4j(is_admin=True)
```

## Migration Detection

The system automatically detects:
- ✅ **New annotations** → Creates appropriate schemas
- ✅ **Updated annotations** → Modifies existing schemas  
- ✅ **Removed annotations** → Cleans up schemas
- ✅ **Relationship changes** → Updates graph connections
- ✅ **Index configuration changes** → Updates search mappings

## Integration with Weave

The annotation system is seamlessly integrated into Weave:

1. **Location**: `weave/bin/modules/annotations/`
2. **Migration Detection**: `annotation_migration_detector.py`
3. **CLI Integration**: Enhanced `weave migrate create --autogenerate`
4. **Future**: Will be extracted when Weave becomes standalone

## Migration Path

For existing projects:

1. **Add annotations** to existing SQLAlchemy models
2. **Run autogenerate** - `weave migrate create <db> "add multi-store" --autogenerate`
3. **Apply migrations** - `weave migrate up`
4. **Use new capabilities** in application code

No separate annotation management needed!

## Next Steps

When Weave is extracted as a standalone library:

1. **Package annotations** as part of the Weave library
2. **Publish to PyPI** for broader use
3. **Add more store types** (Redis, MongoDB, etc.)
4. **Enhanced detection** for more complex scenarios
5. **Documentation site** with comprehensive guides

This approach successfully avoids reinventing the ORM wheel while seamlessly adding powerful multi-store capabilities to your existing SQLAlchemy infrastructure through the familiar migration workflow. 