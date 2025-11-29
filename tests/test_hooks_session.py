"""
Tests for SessionStart hook.
Tests written BEFORE implementation (TDD approach).

This hook initializes session state when agent starts:
- Updates ticket status to "Agent Working"
- Loads existing conversation if resuming
- Initializes turn counter from existing state
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.hooks.session_start import session_start_hook


class TestSessionStartHook:
    """Tests for session start hook."""

    def test_hook_updates_status_to_working(self):
        """Should update ticket status to 'Agent Working' on session start."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        with patch("src.hooks.session_start.update_ticket_status") as mock_update:
            with patch("src.hooks.session_start.load_conversation_state", return_value=[]):
                # Call the hook
                session_start_hook(context=mock_context)

                # Should have updated status to "Agent Working"
                mock_update.assert_called_once_with(
                    mock_context._notion_client,
                    "test-ticket-123",
                    "Agent Working"
                )

    def test_hook_loads_existing_conversation(self):
        """Should load existing conversation from Notion."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        existing_conv = [
            {"role": "user", "content": "Previous task", "turn": 0},
            {"role": "assistant", "content": "Previous response", "turn": 1},
        ]

        with patch("src.hooks.session_start.update_ticket_status"):
            with patch("src.hooks.session_start.load_conversation_state", return_value=existing_conv) as mock_load:
                result = session_start_hook(context=mock_context)

                # Should have loaded conversation
                mock_load.assert_called_once()

                # Should return the loaded conversation
                assert result == existing_conv

    def test_hook_initializes_turn_count_from_conversation(self):
        """Should initialize turn counter based on existing conversation."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        existing_conv = [
            {"role": "user", "content": "Task 1", "turn": 0},
            {"role": "assistant", "content": "Response 1", "turn": 1},
            {"type": "tool_use", "tool_name": "bash", "turn": 2},
            {"role": "assistant", "content": "Response 2", "turn": 3},
        ]

        with patch("src.hooks.session_start.update_ticket_status"):
            with patch("src.hooks.session_start.load_conversation_state", return_value=existing_conv):
                session_start_hook(context=mock_context)

                # Turn count should be set to max turn + 1
                assert mock_context._current_turn == 4

    def test_hook_initializes_turn_to_zero_for_new_session(self):
        """Should initialize turn to 0 for new sessions with no conversation."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        with patch("src.hooks.session_start.update_ticket_status"):
            with patch("src.hooks.session_start.load_conversation_state", return_value=[]):
                session_start_hook(context=mock_context)

                # Turn count should remain 0
                assert mock_context._current_turn == 0

    def test_hook_handles_missing_ticket_id(self):
        """Should handle gracefully when ticket_id is missing."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        # No ticket_id
        mock_context._current_ticket_id = None

        with patch("src.hooks.session_start.update_ticket_status") as mock_update:
            with patch("src.hooks.session_start.load_conversation_state") as mock_load:
                # Should not crash
                result = session_start_hook(context=mock_context)

                # Should not have called Notion functions
                assert not mock_update.called
                assert not mock_load.called

                # Should return empty list
                assert result == []

    def test_hook_returns_empty_list_for_new_session(self):
        """Should return empty list for new sessions."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        with patch("src.hooks.session_start.update_ticket_status"):
            with patch("src.hooks.session_start.load_conversation_state", return_value=[]):
                result = session_start_hook(context=mock_context)

                assert result == []

    def test_hook_preserves_conversation_order(self):
        """Should preserve conversation order when loading."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 0

        existing_conv = [
            {"role": "user", "content": "First", "turn": 0},
            {"role": "assistant", "content": "Second", "turn": 1},
            {"role": "user", "content": "Third", "turn": 2},
        ]

        with patch("src.hooks.session_start.update_ticket_status"):
            with patch("src.hooks.session_start.load_conversation_state", return_value=existing_conv):
                result = session_start_hook(context=mock_context)

                # Order should be preserved
                assert len(result) == 3
                assert result[0]["content"] == "First"
                assert result[1]["content"] == "Second"
                assert result[2]["content"] == "Third"
