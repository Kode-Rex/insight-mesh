# Weave Domain-Context-Tool System

This document explains the domain-driven architecture extension for Weave that provides semantic modeling, context-aware RAG, and scoped tool permissions.

## Overview

The domain-context-tool hierarchy extends your existing `config.json` service registry with semantic modeling:

- **Domains**: Entity schemas (person, messages, channels)
- **Contexts**: Scoped interactions + data views (conversations, threads)  
- **Tools**: Access, wiring, and permissioning (slack, webcat, gmail)

## File Structure

```
.weave/
├── config.json            # Existing services, databases, mcp
├── domains/
│   ├── person.yaml        # Person domain definition
│   ├── messages.yaml      # Messages domain definition
│   └── channels.yaml      # Channels domain definition
├── contexts/
│   └── conversations.yaml # Conversation context definition
├── tools/
│   ├── slack.yaml         # Slack tool with scoped permissions
│   └── webcat.yaml        # Web search tool configuration
└── weave.dev              # Top-level CLI/dev UX config
```

## Domain Definitions

Domains map your existing SQLAlchemy models to semantic entities:

```yaml
# .weave/domains/person.yaml
domain: person
description: "Represents people in the system"

schemas:
  sql: 
    insightmesh: "insightmesh_users"
    slack: "slack_users"
  neo4j: "(:Person)"
  elastic: "person_index"

contexts:
  - messages
  - tasks
  - channels

tools:
  - slack
  - webcat
```

## Context Definitions

Contexts define scoped data views and interactions:

```yaml
# .weave/contexts/conversations.yaml
context: conversations
description: "Threaded conversations across platforms"

domains:
  - messages
  - person
  - channels

sources:
  - database: insightmesh
    table: conversations
    joins:
      - table: messages
        on: "conversations.id = messages.conversation_id"
```

## Tool Definitions

Tools define access patterns and permissions per context:

```yaml
# .weave/tools/slack.yaml
tool: slack
type: mcp
description: "Slack integration"

contexts:
  - messages:
      access:
        roles: [analyst, support, admin]
        scopes: [read, write]
      permissions:
        read: ["channel:history", "im:history"]
        write: ["chat:write"]
```

## CLI Usage

The domain system extends your existing weave CLI:

### List Domains
```bash
weave domain list
weave domain show person
```

### List Contexts
```bash
weave context list
weave context list --domain person
weave context show conversations
```

### Context Injection
```bash
weave context inject --domain person --context messages --user-id 123
```

This returns:
- Schema references across databases
- Tool permissions for the user
- Data sources (RAG, SQL, etc.)
- Tracing metadata

### Tool Management
```bash
weave tool list
weave tool list --domain person
weave tool show slack
```

### Schema Inspection
```bash
weave schema
weave schema --domain person
```

## Integration with Existing Code

The domain loader bridges YAML configs with your existing SQLAlchemy models:

```python
from weave.domain_loader import get_loader

# Load domain configuration
loader = get_loader()

# Get schema mappings for a domain
schemas = loader.get_domain_schemas('person')
# Returns: {'sql': {'insightmesh': 'insightmesh_users', 'slack': 'slack_users'}}

# Inject context for agent execution
context = loader.inject_context('person', 'messages', 'user-123')
# Returns: schemas, sources, tools, permissions for this domain/context/user
```

## Runtime Behavior

When enabled, the system provides:

1. **Domain-aware agent context injection**: Agents automatically get relevant schemas, tools, and permissions
2. **Scoped tool registration**: Tools are only available in appropriate contexts
3. **Observable execution**: OpenTelemetry spans include domain, context, tool metadata
4. **Permission enforcement**: Role-based access control per domain/context

## Migration from Current Structure

Your existing `domain/` folder with SQLAlchemy models remains unchanged. The new YAML configs provide a semantic layer on top:

- `domain/insightmesh/user.py` → `.weave/domains/person.yaml` (references the table)
- `domain/slack/user.py` → `.weave/domains/person.yaml` (references the table)
- MCP tools in `config.json` → `.weave/tools/*.yaml` (adds context scoping)

## Development Workflow

1. **Define domains** for your core entities (person, messages, etc.)
2. **Define contexts** for specific use cases (conversations, analytics, etc.)
3. **Configure tools** with appropriate permissions per context
4. **Use CLI** to inspect and test domain/context injection
5. **Integrate** with agents using the domain loader

The system is designed to be additive - your existing services and databases continue to work unchanged, while gaining semantic modeling and context-aware behavior. 