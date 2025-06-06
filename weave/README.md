# Weave

A Rails-like tool for managing environment variables, secrets, migrations, and services for the Insight Mesh project. Weave is designed to make managing your development environment easier.

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

### Environment Variables

List all environment variables:
```
weave env list
```

Set an environment variable:
```
weave env set KEY VALUE
```

Get an environment variable:
```
weave env get KEY
```

### Database Migrations

Create a new migration:
```
weave db create create_users_table
```

Run migrations:
```
weave db migrate
```

Show migration status:
```
weave db status
```

Rollback migrations:
```
weave db rollback
```

### Vault Secrets

Initialize the vault:
```
weave vault init
```

Set a secret:
```
weave vault set SECRET_KEY secret_value
```

Get a secret:
```
weave vault get SECRET_KEY
```

List all secrets:
```
weave vault list
```

### Services

List all running services:
```
weave service list
```

Open a service in the browser:
```
weave service open service_name
```

### Logs

View logs for all services:
```
weave logs
```

View logs for a specific service:
```
weave logs service_name
```

Follow logs in real-time:
```
weave logs -f [service_name]
```

**Special Case: RAG Logs**

Although "rag" is not a service, you can view the RAG (Retrieval Augmented Generation) logs from the LiteLLM container using:
```
weave logs rag
```

This is a special parameter handled by the logs command to extract and filter RAG handler logs from the LiteLLM container.

Follow RAG logs in real-time:
```
weave logs rag -f
```

Show more detailed RAG logs without filtering:
```
weave logs rag --verbose
```

## Configuration

Weave uses a configuration file to map Docker containers to logical services. This configuration is stored in `.weave/config.json` in the project root.

The configuration file has the following structure:

```json
{
    "project_id": "your-project-id",
    "name": "Your Project Name",
    "services": {
        "service-id": {
            "display_name": "Human-readable service name",
            "description": "Service description",
            "images": ["image:tag", "another-image:tag"],
            "container_patterns": ["container-name-pattern"]
        }
    }
}
```

- `project_id`: The identifier used for Docker containers prefix
- `name`: The human-readable name of your project
- `services`: A map of service definitions
  - `service-id`: A unique identifier for the service
    - `display_name`: A human-readable name for the service
    - `description`: A brief description of the service
    - `images`: An array of Docker image patterns to match
    - `container_patterns`: An array of container name patterns to match

When running `weave service list`, containers are grouped by their matching service based on the container name or image patterns.

## Options

Many commands support additional options. Use `--help` with any command to see available options:
```
weave service list --help
```

## Tip: Add to Your Shell Profile

To automatically activate the environment when you open a terminal, add this to your `~/.zshrc` or `~/.bashrc`:

```bash
# Automatically activate weave environment
if [ -f "/path/to/insight-mesh/weave/venv/bin/activate" ]; then
    source /path/to/insight-mesh/weave/venv/bin/activate
fi
```

Replace `/path/to/insight-mesh/weave` with the actual path to your weave directory. 