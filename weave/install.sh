#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing Weave...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get version to be installed from setup.py
NEW_VERSION=$(grep "version=" "$SCRIPT_DIR/setup.py" | sed 's/.*version="\([^"]*\)".*/\1/')
echo -e "${BLUE}Version to be installed: ${GREEN}$NEW_VERSION${NC}"

# Check if weave is already installed and get current version
if command -v weave &> /dev/null; then
    echo -e "${YELLOW}Checking current installation...${NC}"
    # Test version from the original directory before changing to script directory
    CURRENT_VERSION=$(cd "$(dirname "$SCRIPT_DIR")" && weave --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    if [ "$CURRENT_VERSION" != "unknown" ]; then
        echo -e "${BLUE}Current version: ${YELLOW}$CURRENT_VERSION${NC}"
        if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
            echo -e "${GREEN}✅ Same version - reinstalling/updating dependencies${NC}"
        else
            # Simple version comparison (works for semantic versioning)
            if printf '%s\n%s\n' "$CURRENT_VERSION" "$NEW_VERSION" | sort -V -C; then
                echo -e "${GREEN}⬆️  Upgrading from $CURRENT_VERSION to $NEW_VERSION${NC}"
            else
                echo -e "${YELLOW}⬇️  Installing $NEW_VERSION (currently have $CURRENT_VERSION)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Weave found but version could not be determined${NC}"
    fi
else
    echo -e "${GREEN}🆕 Fresh installation${NC}"
fi

echo ""

# Find python - try python3, then python
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}Error: Python is not installed. Please install Python 3.11 first.${NC}"
    exit 1
fi

# Find pip - try pip3, then pip
if command -v pip3 &> /dev/null; then
    PIP="pip3"
elif command -v pip &> /dev/null; then
    PIP="pip"
else
    echo -e "${RED}Error: pip is not installed. Please install pip first.${NC}"
    exit 1
fi

# Change to the weave directory
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Using Python: $PYTHON${NC}"
echo -e "${YELLOW}Using Pip: $PIP${NC}"

# Detect Python version
PYTHON_VERSION=$($PYTHON --version | awk '{print $2}')
echo -e "${YELLOW}Python version: $PYTHON_VERSION${NC}"

# Create a virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install requirements and package in development mode
echo -e "${YELLOW}Installing dependencies and package...${NC}"
pip install -r requirements.txt
pip install -e .

# Update PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Adding ~/.local/bin to PATH...${NC}"
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to shell profile files if they exist
    for PROFILE in ~/.bash_profile ~/.bashrc ~/.zshrc; do
        if [ -f "$PROFILE" ]; then
            if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$PROFILE"; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$PROFILE"
                echo -e "${YELLOW}Added PATH to $PROFILE${NC}"
            fi
        fi
    done
fi

# Create a global wrapper script that activates the virtual environment
WEAVE_PROJECT_DIR="$(pwd)"
WRAPPER_PATH="$HOME/.local/bin/weave"
mkdir -p "$HOME/.local/bin"

echo -e "${YELLOW}Creating global wrapper script at $WRAPPER_PATH...${NC}"
cat > "$WRAPPER_PATH" <<EOL
#!/bin/bash
# Global wrapper script for weave that activates the virtual environment

# Activate the virtual environment
source "$WEAVE_PROJECT_DIR/venv/bin/activate"

# Run the weave command from the virtual environment
"$WEAVE_PROJECT_DIR/venv/bin/weave" "\$@"
EOL

chmod +x "$WRAPPER_PATH"

echo -e "${GREEN}✅ Weave has been installed successfully!${NC}"
echo -e "${BLUE}📦 Installed version: ${GREEN}$NEW_VERSION${NC}"
echo -e "${BLUE}🌍 You can now use 'weave' command from anywhere.${NC}"

# Show a test command
echo -e "${YELLOW}🧪 Try running these commands to verify installation:${NC}"
echo -e "${BLUE}weave --version${NC}"
echo -e "${BLUE}weave --help${NC}" 