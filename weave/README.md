# Weave

A Rails-like tool for managing environment variables, secrets, migrations, and services for the Insight Mesh project. Weave is designed to make managing your development environment easier with schema-specific database migrations and comprehensive service management.

## Requirements

- Python 3.x (3.11 recommended)
- Docker and Docker Compose

## Installation

1. Run the installation script:
   ```
   ./install.sh
   ```

   This script will:
    - Create a Python virtual environment
    - Install the required dependencies
    - Create a symlink to the weave script in ~/.local/bin
    - Add ~/.local/bin to your PATH (if needed)

2. **Important**: The install script creates a wrapper that automatically activates the virtual environment when you run weave commands.

## Usage

### Database Management

Weave supports multiple database schemas with separate migration directories for each schema (currently `insightmesh` and `slack`).

#### Migration Commands

**Run migrations:**
```bash
# Migrate all databases
weave db migrate

# Migrate specific database
weave db migrate slack
weave db migrate insightmesh

# Preview what would be migrated (dry-run)
weave db migrate --dry-run
weave db migrate slack --dry-run

# Skip database creation step
weave db migrate --skip-db-creation
```

**Check migration status:**
```bash
# Show status for all databases
weave db status

# Show status for specific database
weave db status slack
weave db status insightmesh
```

**Create new migrations:**
```bash
# Create a new migration for a specific database
weave db create slack "add user preferences table"
weave db create insightmesh "add message threading"

# Auto-generate migration based on model changes
weave db create slack "auto detected changes" --auto

# Preview what migration would be created
weave db create slack "test migration" --dry-run
```

**Rollback migrations:**
```bash
# Rollback one migration
weave db rollback slack

# Rollback to specific revision
weave db rollback slack --revision 001

# Preview what would be rolled back
weave db rollback slack --dry-run
```

**View migration history:**
```bash
# Show migration history for a database
weave db history slack
weave db history insightmesh
```

**Reset database:**
```bash
# Reset a database (rollback all migrations and re-run them)
# WARNING: This destroys all data!
weave db reset slack

# Reset without confirmation prompt
weave db reset slack --force
```

**Seed databases:**
```bash
# Seed all databases with sample data
weave db seed

# Seed specific database
weave db seed slack
```

#### Migration Structure

Weave uses schema-specific migration directories:
```
.weave/migrations/
├── insightmesh/
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── insightmesh_001_initial.py
└── slack/
    ├── alembic.ini
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── slack_001_initial.py
```

Each schema has its own:
- Configuration file (`alembic.ini`)
- Environment setup (`env.py`) with correct metadata imports
- Migration template (`script.py.mako`)
- Version history (`versions/` directory)

### Environment Variables

List all environment variables:
```bash
weave env list
```

Set an environment variable:
```bash
weave env set KEY VALUE
```

Get an environment variable:
```bash
weave env get KEY
```

### Vault Secrets

Initialize the vault:
```bash
weave vault init
```

Set a secret:
```bash
weave vault set SECRET_KEY secret_value
```

Get a secret:
```bash
weave vault get SECRET_KEY
```

List all secrets:
```bash
weave vault list
```

### Services

List all running services:
```bash
weave service list
```

Open a service in the browser:
```bash
weave service open service_name
```

### Logs

View logs for all services:
```bash
weave logs
```

View logs for a specific service:
```bash
weave logs service_name
```

Follow logs in real-time:
```bash
weave logs -f [service_name]
```

**Special Case: RAG Logs**

Although "rag" is not a service, you can view the RAG (Retrieval Augmented Generation) logs from the LiteLLM container using:
```bash
weave logs rag
```

This is a special parameter handled by the logs command to extract and filter RAG handler logs from the LiteLLM container.

Follow RAG logs in real-time:
```bash
weave logs rag -f
```

Show more detailed RAG logs without filtering:
```bash
weave logs rag --verbose
```

## Configuration

Weave uses a configuration file to manage services and databases. This configuration is stored in `.weave/config.json` in the project root.

### Database Configuration

The `databases` section defines which databases are managed by weave:

```json
{
    "databases": {
        "slack": {
            "description": "Slack integration data (users, channels, messages)",
            "managed_by": "weave",
            "migrations": true,
            "metadata": "SlackBase"
        },
        "insightmesh": {
            "description": "Core MCP server data (users, contexts, conversations)",
            "managed_by": "weave", 
            "migrations": true,
            "metadata": "MCPBase"
        }
    }
}
```

### Service Configuration

The `services` section maps Docker containers to logical services:

```json
{
    "project_name": "your-project-name",
    "services": {
        "service-id": {
            "display_name": "Human-readable service name",
            "description": "Service description",
            "images": ["image:tag", "another-image:tag"],
            "container_patterns": ["container-name-pattern"],
            "depends_on": ["postgres", "redis"]
        }
    }
}
```

- `project_name`: The prefix used for Docker containers
- `services`: A map of service definitions
  - `service-id`: A unique identifier for the service
    - `display_name`: A human-readable name for the service
    - `description`: A brief description of the service
    - `images`: An array of Docker image patterns to match
    - `container_patterns`: An array of container name patterns to match
    - `depends_on`: Optional array of services this service depends on

When running `weave service list`, containers are grouped by their matching service based on the container name or image patterns.

## Command Help

All commands support `--help` to show available options:
```bash
weave --help
weave db --help
weave db migrate --help
weave service --help
```

## Development Tips

### Automatic Environment Activation

To automatically activate the environment when you open a terminal, add this to your `~/.zshrc` or `~/.bashrc`:

```bash
# Automatically activate weave environment
if [ -f "/path/to/insight-mesh/weave/venv/bin/activate" ]; then
    source /path/to/insight-mesh/weave/venv/bin/activate
fi
```

Replace `/path/to/insight-mesh/weave` with the actual path to your weave directory.

### Migration Best Practices

1. **Always create migrations for schema changes**: Use `weave db create` to generate migration files
2. **Test migrations**: Use `--dry-run` options to preview changes before applying
3. **Use descriptive messages**: Make migration messages clear and descriptive
4. **Review auto-generated migrations**: When using `--auto`, always review the generated migration before applying
5. **Backup before major changes**: Consider backing up your database before running complex migrations 