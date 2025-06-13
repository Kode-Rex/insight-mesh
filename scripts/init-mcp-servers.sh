#!/bin/bash

# MCP Server Initialization Script
# This script syncs MCP servers from weave config to LiteLLM database
# Designed to be run on container startup

set -e

# Configuration
LITELLM_URL="${LITELLM_URL:-http://litellm:4000}"
LITELLM_API_KEY="${LITELLM_API_KEY:-sk-litellm-master-key-123456}"
WAIT_FOR_SERVICE="${WAIT_FOR_SERVICE:-true}"
MAX_RETRIES="${MAX_RETRIES:-5}"
RETRY_DELAY="${RETRY_DELAY:-10}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Check if weave is available
check_weave() {
    if ! command -v weave &> /dev/null; then
        log_error "weave command not found. Make sure weave is installed and in PATH."
        return 1
    fi
    return 0
}

# Wait for LiteLLM service to be ready
wait_for_litellm() {
    if [ "$WAIT_FOR_SERVICE" != "true" ]; then
        log "Skipping service wait (WAIT_FOR_SERVICE=false)"
        return 0
    fi

    log "Waiting for LiteLLM service at $LITELLM_URL..."
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s -f "$LITELLM_URL/health" > /dev/null 2>&1; then
            log_success "LiteLLM service is ready"
            return 0
        fi
        
        log_warning "LiteLLM not ready, attempt $i/$MAX_RETRIES. Waiting ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    done
    
    log_error "LiteLLM service not ready after $MAX_RETRIES attempts"
    return 1
}

# Check if MCP is enabled in LiteLLM
check_mcp_enabled() {
    log "Checking if MCP is enabled in LiteLLM..."
    
    response=$(curl -s "$LITELLM_URL/mcp/enabled" 2>/dev/null || echo '{"enabled": false}')
    enabled=$(echo "$response" | grep -o '"enabled":[^,}]*' | cut -d':' -f2 | tr -d ' "')
    
    if [ "$enabled" = "true" ]; then
        log_success "MCP is enabled in LiteLLM"
        return 0
    else
        log_error "MCP is not enabled in LiteLLM"
        return 1
    fi
}

# Initialize MCP servers using weave
init_mcp_servers() {
    log "Initializing MCP servers from weave config..."
    
    # Change to the project directory (where .weave/config.json is located)
    if [ -n "$PROJECT_ROOT" ]; then
        cd "$PROJECT_ROOT"
    fi
    
    # Check if weave config exists
    if [ ! -f ".weave/config.json" ]; then
        log_error "Weave config file not found at .weave/config.json"
        return 1
    fi
    
    # Run weave tool init
    if weave tool init \
        --litellm-url "$LITELLM_URL" \
        --api-key "$LITELLM_API_KEY" \
        --wait-for-service; then
        log_success "MCP servers initialized successfully"
        return 0
    else
        log_error "Failed to initialize MCP servers"
        return 1
    fi
}

# Main execution
main() {
    log "Starting MCP server initialization..."
    log "Configuration:"
    log "  LiteLLM URL: $LITELLM_URL"
    log "  Wait for service: $WAIT_FOR_SERVICE"
    log "  Max retries: $MAX_RETRIES"
    log "  Retry delay: ${RETRY_DELAY}s"
    
    # Check prerequisites
    if ! check_weave; then
        exit 1
    fi
    
    # Wait for LiteLLM service
    if ! wait_for_litellm; then
        exit 1
    fi
    
    # Check MCP is enabled
    if ! check_mcp_enabled; then
        exit 1
    fi
    
    # Initialize MCP servers
    if ! init_mcp_servers; then
        exit 1
    fi
    
    log_success "MCP server initialization completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "MCP Server Initialization Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Environment Variables:"
        echo "  LITELLM_URL          LiteLLM proxy URL (default: http://litellm:4000)"
        echo "  LITELLM_API_KEY      LiteLLM API key (default: sk-litellm-master-key-123456)"
        echo "  WAIT_FOR_SERVICE     Wait for LiteLLM service (default: true)"
        echo "  MAX_RETRIES          Maximum retry attempts (default: 5)"
        echo "  RETRY_DELAY          Delay between retries in seconds (default: 10)"
        echo "  PROJECT_ROOT         Project root directory (optional)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Use default settings"
        echo "  LITELLM_URL=http://localhost:4000 $0  # Custom LiteLLM URL"
        echo "  WAIT_FOR_SERVICE=false $0             # Skip service wait"
        exit 0
        ;;
    --dry-run)
        log "DRY RUN MODE - would initialize MCP servers with:"
        log "  LiteLLM URL: $LITELLM_URL"
        log "  API Key: ${LITELLM_API_KEY:0:10}..."
        log "  Wait for service: $WAIT_FOR_SERVICE"
        exit 0
        ;;
    "")
        # No arguments, run normally
        main
        ;;
    *)
        log_error "Unknown argument: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac 