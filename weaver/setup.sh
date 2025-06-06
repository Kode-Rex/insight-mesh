#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Weaver tool...${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install requirements
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Make the script executable
echo -e "${YELLOW}Making script executable...${NC}"
chmod +x bin/weaver

# Create symlink for easy access
if [ ! -f "/usr/local/bin/weaver" ]; then
    echo -e "${YELLOW}Creating symlink to /usr/local/bin/weaver...${NC}"
    ln -sf "$(pwd)/bin/weaver" /usr/local/bin/weaver
else
    echo -e "${YELLOW}Updating symlink to /usr/local/bin/weaver...${NC}"
    rm -f /usr/local/bin/weaver
    ln -sf "$(pwd)/bin/weaver" /usr/local/bin/weaver
fi

echo -e "${GREEN}Weaver has been installed successfully!${NC}"
echo -e "${GREEN}You can now use the 'weaver' command from anywhere.${NC}"
echo -e "${BLUE}Try running 'weaver --help' to see available commands.${NC}" 