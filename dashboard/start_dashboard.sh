#!/usr/bin/env bash

################################################################################
# Dashboard Startup Script
# Starts both backend (FastAPI) and frontend (React) in separate processes
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Ralph Wiggum Dashboard..."
echo ""

# Load environment
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source <(sed 's/\r$//' "$PROJECT_ROOT/.env")
    set +a
    echo "✓ Loaded environment from .env"
else
    echo "⚠️  Warning: .env file not found"
fi

# Export ticket dir
export CLAUDE_TICKET_DIR="$PROJECT_ROOT/tickets"

echo ""
echo "Backend will run on: http://localhost:8000"
echo "Frontend will run on: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start backend in background
cd "$PROJECT_ROOT"
echo "Starting backend..."
uv run python dashboard/backend/app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend in background
cd "$SCRIPT_DIR/frontend"
echo "Starting frontend..."
npm run dev &
FRONTEND_PID=$!

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down dashboard..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✓ Dashboard stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
