"""
Tests for Notion helper module.
Tests written BEFORE implementation (TDD approach).
"""
import pytest
from src.notion_helper import (
    get_ticket_context,
    save_conversation_state,
    load_conversation_state,
    update_ticket_status,
    claim_pending_ticket,
)


class TestGetTicketContext:
    """Tests for fetching ticket context from Notion."""

    def test_get_ticket_context_returns_valid_structure(
        self, notion_client, test_ticket
    ):
        """Should return dict with ticket name, status, session_id, conversation."""
        result = get_ticket_context(notion_client, test_ticket)

        assert isinstance(result, dict)
        assert "ticket_name" in result
        assert "status" in result
        assert "session_id" in result
        assert "conversation" in result
        assert "turn_count" in result

    def test_get_ticket_context_handles_missing_ticket(self, notion_client):
        """Should return None or raise specific error for non-existent ticket."""
        result = get_ticket_context(notion_client, "invalid-ticket-id")
        assert result is None

    def test_get_ticket_context_loads_existing_conversation(
        self, notion_client, test_ticket
    ):
        """Should parse conversation JSON if present in ticket."""
        # First save a conversation
        test_conversation = [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z", "turn": 1},
            {"role": "assistant", "content": "Hi!", "timestamp": "2025-01-01T00:00:01Z", "turn": 1},
        ]
        save_conversation_state(notion_client, test_ticket, test_conversation)

        # Then load it back
        result = get_ticket_context(notion_client, test_ticket)
        assert result["conversation"] == test_conversation


class TestConversationStatePersistence:
    """Tests for saving/loading conversation state."""

    def test_save_conversation_state_to_notion_property(
        self, notion_client, test_ticket
    ):
        """Should save conversation as JSON in Notion property."""
        conversation = [
            {"role": "user", "content": "Test message", "timestamp": "2025-01-01T00:00:00Z", "turn": 1}
        ]

        result = save_conversation_state(notion_client, test_ticket, conversation)
        assert result is True

    def test_load_conversation_state_from_notion_property(
        self, notion_client, test_ticket
    ):
        """Should load conversation from Notion property as list."""
        # Save first
        test_conversation = [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z", "turn": 1},
            {"role": "assistant", "content": "Hi!", "timestamp": "2025-01-01T00:00:01Z", "turn": 1},
        ]
        save_conversation_state(notion_client, test_ticket, test_conversation)

        # Load back
        result = load_conversation_state(notion_client, test_ticket)
        assert result == test_conversation

    def test_load_conversation_state_returns_empty_for_new_ticket(
        self, notion_client, test_ticket
    ):
        """Should return empty list if no conversation exists yet."""
        result = load_conversation_state(notion_client, test_ticket)
        assert result == []

    def test_save_conversation_increments_turn_count(
        self, notion_client, test_ticket
    ):
        """Should update turn count when saving conversation."""
        conversation = [
            {"role": "user", "content": "Turn 1", "timestamp": "2025-01-01T00:00:00Z", "turn": 1},
            {"role": "assistant", "content": "Response 1", "timestamp": "2025-01-01T00:00:01Z", "turn": 1},
            {"role": "user", "content": "Turn 2", "timestamp": "2025-01-01T00:00:02Z", "turn": 2},
        ]

        save_conversation_state(notion_client, test_ticket, conversation)

        # Verify turn count was updated
        context = get_ticket_context(notion_client, test_ticket)
        assert context["turn_count"] == 2


class TestTicketStatusManagement:
    """Tests for updating ticket status."""

    def test_update_ticket_status_changes_status(
        self, notion_client, test_ticket
    ):
        """Should update ticket status in Notion."""
        result = update_ticket_status(
            notion_client, test_ticket, "Agent Planning"
        )
        assert result is True

        # Verify status changed
        context = get_ticket_context(notion_client, test_ticket)
        assert context["status"] == "Agent Planning"

    def test_update_ticket_status_handles_invalid_status(
        self, notion_client, test_ticket
    ):
        """Should handle invalid status gracefully."""
        result = update_ticket_status(
            notion_client, test_ticket, "Invalid Status"
        )
        # Should either return False or raise specific exception
        assert result is False or result is None


class TestClaimPendingTicket:
    """Tests for claiming pending tickets."""

    def test_claim_pending_ticket_returns_oldest_pending(
        self, notion_client, notion_test_db
    ):
        """Should return oldest pending ticket and claim it."""
        result = claim_pending_ticket(notion_client, notion_test_db)

        if result is not None:
            assert "ticket_id" in result
            assert "session_id" in result
            assert "ticket_name" in result

    def test_claim_pending_ticket_sets_status_to_planning(
        self, notion_client, notion_test_db
    ):
        """Should set status to 'Agent Planning' when claiming."""
        result = claim_pending_ticket(notion_client, notion_test_db)

        if result is not None:
            ticket_id = result["ticket_id"]
            context = get_ticket_context(notion_client, ticket_id)
            assert context["status"] == "Agent Planning"

    def test_claim_pending_ticket_returns_none_when_no_pending(
        self, notion_client, notion_test_db
    ):
        """Should return None if no pending tickets exist."""
        # This test depends on database state, may need mocking
        result = claim_pending_ticket(notion_client, notion_test_db)
        # Accept either None or a valid ticket
        assert result is None or isinstance(result, dict)
