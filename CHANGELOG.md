# Changelog

## v0.3.0 - TDD Refactoring (2025-11)
- Added structured logging with rotation (10MB, 5 backups)
- Replaced all print() statements with logger calls
- Added comprehensive test suite (24 tests, 100% passing)
- Removed unused file types (.question, .done)
- Added file path validation and error handling

## v0.2.0 - Single-Ticket Workflow (2025-11)
- Added ticket claiming mechanism (Pending → Agent Planning)
- Simplified status flow (removed Ready to Start)
- Human-controlled completion (only humans can mark Done)
- Exit on Done status
- Dashboard: Added Pending and Agent Planning columns

## v0.1.0 - Brownfield Planning + Dashboard (2025-11)
- Added Planning status with auto-exploration
- Removed `mark_ticket_done` tool (human-controlled only)
- Built web dashboard (FastAPI + React + Tailwind)
- Kanban board with 4 columns
- Live stats and auto-refresh (3sec polling)
- Session tracking with turn counts
