#!/bin/bash
# Manual integration test for schedule proposal
# This script starts the test agent and sends a scheduling request

set -e

echo "=== Schedule Proposal Integration Test ==="
echo ""

# Check if agent is already running
if curl -s http://localhost:8080/.well-known/agent.json > /dev/null 2>&1; then
    echo "Agent already running on port 8080"
else
    echo "Starting test agent..."
    python main.py &
    AGENT_PID=$!
    sleep 3

    # Check if agent started successfully
    if ! curl -s http://localhost:8080/.well-known/agent.json > /dev/null 2>&1; then
        echo "ERROR: Agent failed to start"
        kill $AGENT_PID 2>/dev/null || true
        exit 1
    fi
    echo "Agent started (PID: $AGENT_PID)"
fi

echo ""
echo "=== Sending scheduling request ==="
echo ""

# Send a scheduling request
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --no-buffer \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Schedule a daily standup reminder every weekday at 9am"}]
      }
    },
    "id": "test-schedule-1"
  }'

echo ""
echo ""
echo "=== Test complete ==="

# If we started the agent, stop it
if [ -n "$AGENT_PID" ]; then
    echo "Stopping agent (PID: $AGENT_PID)..."
    kill $AGENT_PID 2>/dev/null || true
fi
