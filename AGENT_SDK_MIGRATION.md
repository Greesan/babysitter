# Agent SDK Migration Plan

## Overview

Migrating from Ralph Wiggum loop (bash + MCP polling) to Agent SDK (Python + built-in hooks).

## ✅ Agent SDK Uses Pro Subscription (No API Costs!)

**IMPORTANT:** The Agent SDK can use your Claude Code Pro/Max subscription instead of API credits.

### How to Avoid API Charges:

1. **Do NOT set `ANTHROPIC_API_KEY` environment variable**
   ```bash
   # Make sure this is NOT set
   unset ANTHROPIC_API_KEY

   # Remove from .env if present
   # ANTHROPIC_API_KEY=sk-...  # DELETE THIS LINE
   ```

2. **Authenticate with subscription account**
   - When Claude Code prompts, choose "Log in with your subscription account"
   - Usage counts against Pro/Max plan, not API credits

3. **Agent SDK → Claude Code CLI → Pro Subscription**
   - Agent SDK uses Claude Code CLI under the hood
   - No separate API billing

**Warning:** If `ANTHROPIC_API_KEY` is set, you WILL be charged API rates instead of using your subscription!

## Key Changes

### Current (Ralph Wiggum)
```
rwLOOP.sh (infinite while loop)
  ├─ Polls Notion every 5s for tickets
  ├─ Starts Claude with --session-id
  ├─ ask_human MCP tool = hack to pause loop
  ├─ resume_poll.py checks for responses
  └─ Resumes with --resume
```

### Target (Agent SDK)
```
agent.py (single execution)
  ├─ Query Notion ONCE on startup
  ├─ ClaudeSDKClient manages conversation
  ├─ Built-in user_input hook (no MCP hack)
  ├─ Frontend sends input via API/webhook
  └─ Agent exits when task done
```

## Migration Steps

### Phase 1: Setup Agent SDK
- [x] Create agent-sdk branch
- [ ] Install claude-agent-sdk package
- [ ] Create src/agent.py structure
- [ ] Add .mcp.json for Notion server

### Phase 2: Notion Integration
- [ ] Keep scripts/notion_mcp_server.py as MCP server
- [ ] Update to work as external MCP (not in-process)
- [ ] Remove ask_human tool (use built-in user input)
- [ ] Add UserPromptSubmit hook for Notion updates

### Phase 3: Replace Loop Logic
- [ ] Create src/agent.py with ClaudeSDKClient
- [ ] Query Notion for pending ticket on startup (once)
- [ ] Use session management for multi-turn
- [ ] Remove rwLOOP.sh infinite loop
- [ ] Create simple agent_start.py trigger script

### Phase 4: Frontend Integration
- [ ] Update dashboard to call Agent SDK API
- [ ] Replace polling with webhooks/events
- [ ] Use integrateThis.* files for new UI
- [ ] Stream agent output to frontend

### Phase 5: Testing & Cleanup
- [ ] Test single-ticket workflow
- [ ] Test multi-turn conversations
- [ ] Update tests for Agent SDK
- [ ] Remove old polling scripts

## Architecture Comparison

### File Structure Changes

**Before:**
```
rwLOOP.sh                    # Infinite loop
scripts/
  ├─ notion_mcp_server.py    # MCP tool: ask_human
  ├─ resume_poll.py          # Polls Notion
  ├─ get_or_create_session.py
  └─ cleanup_tickets.py
```

**After:**
```
src/
  ├─ agent.py                # Main Agent SDK client
  ├─ mcp_servers/
  │   └─ notion_server.py    # External MCP (no ask_human)
  └─ hooks/
      └─ user_prompt.py      # Notion updates on input
.mcp.json                    # MCP config
agent_start.py               # Simple trigger (replaces rwLOOP)
```

### Notion Flow Changes

**Before:**
1. rwLOOP polls Notion every 5s
2. Finds pending ticket → starts Claude
3. Claude calls ask_human MCP → creates/updates Notion
4. Claude suspends
5. Human responds + checks checkbox
6. resume_poll.py detects → resumes Claude

**After:**
1. agent_start.py triggered (webhook/manual/cron)
2. agent.py queries Notion ONCE → finds pending ticket
3. ClaudeSDKClient starts with ticket description
4. Claude needs input → built-in user_input hook
5. Hook updates Notion with question
6. Frontend/Notion sends response via Agent SDK API
7. Agent continues automatically
8. Agent exits when done

## Key Benefits

✅ No infinite loop (cleaner resource usage)
✅ No polling (event-driven)
✅ No MCP hack for user input (built-in)
✅ Better state management (session-based)
✅ Production-ready (designed for deployment)
✅ Easier testing (no bash, pure Python)

## Migration Risks

⚠️ Session management differences (CLI vs SDK)
⚠️ MCP server needs refactoring (remove ask_human)
⚠️ Frontend needs webhook integration (no polling)
⚠️ Different error handling patterns

## Cost Comparison

### Current (Ralph Wiggum + Pro Subscription)
- ✅ Uses Claude Code CLI
- ✅ Counts against Pro/Max plan
- ✅ $0 additional cost

### Agent SDK (Configured Correctly)
- ✅ Uses Claude Code CLI under the hood
- ✅ Counts against Pro/Max plan (if ANTHROPIC_API_KEY is NOT set)
- ✅ $0 additional cost
- ⚠️ MUST avoid setting ANTHROPIC_API_KEY to prevent API charges

## Next Actions

1. Install Agent SDK: `uv add claude-agent-sdk`
2. Create src/agent.py skeleton
3. Test basic Agent SDK query
4. Incrementally migrate features
