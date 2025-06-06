# Weaver

A simple CLI tool to manage Docker Compose services for the Insight Mesh project. Weaver is scoped to only manage containers belonging to the "insight-mesh" project.

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
    - Create a symlink to the weaver script in ~/.local/bin
    - Add ~/.local/bin to your PATH (if needed)

2. **Important**: The install script creates a wrapper that automatically activates the virtual environment when you run weaver commands.

## Usage

### Start Services

Start all Insight Mesh services in detached mode:
```
weaver up -d
```

Start specific services:
```
weaver up -d -s openwebui litellm
```

### Stop Services

Stop all Insight Mesh services:
```
weaver down
```

Stop and remove volumes:
```
weaver down -v
```

### View Service Status

Show status of all Insight Mesh services:
```
weaver status
```

List running Insight Mesh containers:
```
weaver ps
```

### View Logs

View logs for all Insight Mesh services:
```
weaver logs
```

Follow logs for a specific service:
```
weaver logs -f litellm
```

### Restart Services

Restart all Insight Mesh services:
```
weaver restart
```

Restart a specific service:
```
weaver restart litellm
```

### View Configuration

Show the Docker Compose configuration:
```
weaver config
```

## Options

- `--verbose` or `-v`: Enable verbose output (can be used with any command)

## Examples

Start services in detached mode with verbose output:
```
weaver -v up -d
```

Stop services and remove volumes:
```
weaver down -v
```

View logs for the litellm service:
```
weaver logs litellm
```

## How It Works

Weaver passes the `-p insight-mesh` flag to all Docker Compose commands, ensuring that operations are limited to containers belonging to the Insight Mesh project.

## Tip: Add to Your Shell Profile

To automatically activate the environment when you open a terminal, add this to your `~/.zshrc` or `~/.bashrc`:

```bash
# Automatically activate weaver environment
if [ -f "/path/to/insight-mesh/weaver/venv/bin/activate" ]; then
    source /path/to/insight-mesh/weaver/venv/bin/activate
fi
```

Replace `/path/to/insight-mesh/weaver` with the actual path to your weaver directory. 