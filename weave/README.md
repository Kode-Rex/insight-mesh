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