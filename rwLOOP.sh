#!/usr/bin/env bash

################################################################################
# Ralph Wiggum Loop - Autonomous Claude Code Agent with Human-in-the-Loop
################################################################################
#
# This script implements the "Ralph Wiggum" pattern: a continuous loop that
# runs Claude Code in headless mode, automatically handling:
#   1. Starting new conversations when idle
#   2. Suspending when human input is needed (via Notion tickets)
#   3. Resuming conversations when humans respond
#
# Flow:
#   Claude working → Calls ask_human MCP tool → Creates Notion ticket →
#   Conversation suspends → Human responds in Notion → Loop resumes Claude
#
################################################################################

set -euo pipefail  # Exit on error, undefined variables, pipe failures

#==============================================================================#
# Configuration
#==============================================================================#

# Auto-detect project root (directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"

# Poll interval in seconds (how often to check for ticket responses)
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-5}"

# Verbose logging (set VERBOSE=true for detailed logs)
VERBOSE="${VERBOSE:-false}"

# Derived paths
TICKET_DIR="$PROJECT_ROOT/tickets"
CONVERSATION_DIR="$PROJECT_ROOT/claude_conversations"
ENV_FILE="$PROJECT_ROOT/.env"
PROMPT_FILE="$PROJECT_ROOT/first_prompt.txt"
MCP_CONFIG="$PROJECT_ROOT/mcp-config.json"

#==============================================================================#
# Logging
#==============================================================================#

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)  echo "[$timestamp] ℹ️  $message" ;;
        SUCCESS) echo "[$timestamp] ✓ $message" ;;
        WARN)  echo "[$timestamp] ⚠️  $message" ;;
        ERROR) echo "[$timestamp] ✗ $message" >&2 ;;
        DEBUG)
            if [ "$VERBOSE" = "true" ]; then
                echo "[$timestamp] [DEBUG] $message"
            fi
            ;;
    esac
}

#==============================================================================#
# Validation
#==============================================================================#

validate_environment() {
    log DEBUG "Validating environment..."

    # Check required files exist
    if [ ! -f "$PROMPT_FILE" ]; then
        log ERROR "Missing required file: $PROMPT_FILE"
        log ERROR "Current directory: $PROJECT_ROOT"
        exit 1
    fi

    if [ ! -f "$MCP_CONFIG" ]; then
        log ERROR "Missing required file: $MCP_CONFIG"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        log ERROR "Missing required file: $ENV_FILE"
        exit 1
    fi

    # Check required commands are available
    for cmd in claude uuidgen uv; do
        if ! command -v "$cmd" &> /dev/null; then
            log ERROR "Required command not found: $cmd"
            exit 1
        fi
    done

    log DEBUG "Environment validation passed"
}

#==============================================================================#
# Setup
#==============================================================================#

setup_directories() {
    log DEBUG "Setting up directories..."
    mkdir -p "$CONVERSATION_DIR"
    mkdir -p "$TICKET_DIR"
    log DEBUG "Directories ready"
}

load_environment() {
    log DEBUG "Loading environment variables from $ENV_FILE"

    # Load environment variables from .env (strip Windows line endings)
    set -a
    source <(sed 's/\r$//' "$ENV_FILE")
    set +a

    export CLAUDE_TICKET_DIR="$TICKET_DIR"

    log DEBUG "Environment loaded"
}

#==============================================================================#
# Core Functions
#==============================================================================#

count_pending_tickets() {
    local count=$(ls "$TICKET_DIR"/*.page 2>/dev/null | wc -l)
    echo "$count"
}

start_new_conversation() {
    # Generate a unique session ID for this conversation
    export CLAUDE_SESSION_ID=$(uuidgen)

    log SUCCESS "Starting new conversation (session: $CLAUDE_SESSION_ID)"
    log DEBUG "Loading prompt from $PROMPT_FILE"
    log DEBUG "Using MCP config: $MCP_CONFIG"

    # Start Claude in headless mode
    if cat "$PROMPT_FILE" | claude -p \
        --session-id "$CLAUDE_SESSION_ID" \
        --mcp-config "$MCP_CONFIG" \
        --dangerously-skip-permissions; then
        log DEBUG "Claude exited successfully"
    else
        local exit_code=$?
        log ERROR "Claude exited with code $exit_code"
        exit $exit_code
    fi
}

resume_conversations() {
    log DEBUG "Checking for ticket responses..."

    if uv run python "$PROJECT_ROOT/scripts/resume_poll.py"; then
        log DEBUG "Resume polling completed"
    else
        local exit_code=$?
        log ERROR "Resume polling failed with code $exit_code"
        exit $exit_code
    fi
}

#==============================================================================#
# Main Loop
#==============================================================================#

main() {
    log INFO "Ralph Wiggum loop starting..."
    log INFO "Project root: $PROJECT_ROOT"
    log INFO "Poll interval: ${POLL_INTERVAL_SECONDS}s"
    log INFO "Verbose logging: $VERBOSE"

    # One-time setup
    validate_environment
    setup_directories
    load_environment

    log SUCCESS "Initialization complete"
    echo ""

    # Main loop
    while true; do
        cd "$PROJECT_ROOT" || {
            log ERROR "Failed to cd to $PROJECT_ROOT"
            exit 1
        }

        # Check for pending tickets
        pending_ticket_count=$(count_pending_tickets)

        if [ "$pending_ticket_count" -eq 0 ]; then
            # No pending tickets - start a new conversation
            start_new_conversation
        else
            # Tickets pending - wait for human responses
            log INFO "⏸  Conversation suspended ($pending_ticket_count pending ticket(s))"
        fi

        # Check for human responses and resume conversations
        resume_conversations

        # Loop separator
        if [ "$VERBOSE" = "true" ]; then
            echo ""
            echo "==================== LOOP ITERATION COMPLETE ===================="
            echo ""
        fi

        sleep "$POLL_INTERVAL_SECONDS"
    done
}

# Run main function
main