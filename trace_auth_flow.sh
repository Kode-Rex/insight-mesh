#!/bin/bash

# Trace Authentication Flow Script
# This script helps trace the complete auth flow from Slack → LiteLLM → MCP → Elasticsearch

echo "🔍 Starting Authentication Flow Tracing..."
echo "Press Ctrl+C to stop tracing"
echo ""

# Function to run trace in background and capture PIDs
trace_component() {
    local name="$1"
    local command="$2"
    local filter="$3"
    
    echo "📡 Starting $name trace..."
    if [ -n "$filter" ]; then
        eval "$command | grep -E '$filter'" &
    else
        eval "$command" &
    fi
    echo $! >> /tmp/trace_pids.txt
}

# Clean up any existing PID file
rm -f /tmp/trace_pids.txt

echo "=== 1. SLACK BOT (Auth Token Creation) ==="
trace_component "Slack Bot" "docker logs -f insight-mesh-slack-bot-1" "(auth|token|X-Auth-Token|user_id)"

echo ""
echo "=== 2. RAG HANDLER (Token Extraction) ==="
trace_component "RAG Handler" "weave log rag -f" "(auth|token|X-Auth-Token|metadata|MCP)"

echo ""
echo "=== 3. MCP SERVER (Token Validation & Search) ==="
trace_component "MCP Server" "docker logs -f insight-mesh-mcp-1" "(token|auth|user|email|Elasticsearch|search|permission)"

echo ""
echo "=== 4. ELASTICSEARCH (Query Execution) ==="
trace_component "Elasticsearch" "docker logs -f insight-mesh-elasticsearch-1" "(query|search|POST)"

echo ""
echo "🚀 All traces started! Send a message to your Slack bot to see the flow."
echo "💡 Look for these key patterns:"
echo "   - Slack: 'Added X-Auth-Token header: slack:UXXXXX'"
echo "   - RAG: 'Using auth token from X-Auth-Token header'"
echo "   - MCP: 'Validating token of type Slack'"
echo "   - MCP: 'Searching documents with permission filtering'"
echo "   - ES: Query execution logs"
echo ""
echo "Press Ctrl+C to stop all traces..."

# Wait for user interrupt
trap 'echo ""; echo "🛑 Stopping all traces..."; kill $(cat /tmp/trace_pids.txt 2>/dev/null) 2>/dev/null; rm -f /tmp/trace_pids.txt; echo "✅ All traces stopped."; exit 0' INT

# Keep script running
while true; do
    sleep 1
done 