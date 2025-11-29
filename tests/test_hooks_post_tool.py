"""
Tests for PostToolUse hook.
Tests written BEFORE implementation (TDD approach).

This hook tracks tool usage metadata after each tool execution:
- Extracts tool name, inputs, outputs
- Updates conversation JSON with tool usage
- Increments turn count
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.hooks.post_tool_use import post_tool_use_hook


class TestPostToolUseHook:
    """Tests for post tool use hook."""

    def test_hook_extracts_tool_metadata(self):
        """Should extract tool name, inputs, and outputs from tool use event."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 1

        # Simulate a tool use event
        tool_event = {
            "tool_name": "bash",
            "tool_input": {"command": "ls -la"},
            "tool_output": "file1.txt\nfile2.txt",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=[]):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                # Call the hook
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                # Should have saved conversation with tool metadata
                assert mock_save.called
                call_args = mock_save.call_args[0]
                conversation = call_args[2]

                # Should have tool usage entry
                assert len(conversation) == 1
                tool_entry = conversation[0]
                assert tool_entry["type"] == "tool_use"
                assert tool_entry["tool_name"] == "bash"
                assert tool_entry["tool_input"] == {"command": "ls -la"}
                assert tool_entry["tool_output"] == "file1.txt\nfile2.txt"

    def test_hook_updates_conversation_json(self):
        """Should update conversation JSON in Notion with tool usage."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 2

        existing_conv = [
            {"role": "user", "content": "Run ls", "turn": 0}
        ]

        tool_event = {
            "tool_name": "bash",
            "tool_input": {"command": "ls"},
            "tool_output": "success",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=existing_conv):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                # Should preserve existing conversation and add tool use
                call_args = mock_save.call_args[0]
                conversation = call_args[2]

                assert len(conversation) == 2
                assert conversation[0]["content"] == "Run ls"
                assert conversation[1]["type"] == "tool_use"

    def test_hook_increments_turn_count(self):
        """Should increment turn count after tool use."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 5

        tool_event = {
            "tool_name": "read",
            "tool_input": {"file": "test.py"},
            "tool_output": "def test(): pass",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=[]):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                # Turn should be incremented
                assert mock_context._current_turn == 6

                # Tool use should be recorded with current turn (before increment)
                call_args = mock_save.call_args[0]
                conversation = call_args[2]
                assert conversation[0]["turn"] == 5

    def test_hook_handles_tool_errors(self):
        """Should handle tool errors gracefully and record them."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 1

        tool_event = {
            "tool_name": "bash",
            "tool_input": {"command": "invalid_command"},
            "tool_output": None,
            "error": "Command not found",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=[]):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                # Should not raise exception
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                # Should still record the tool use with error
                call_args = mock_save.call_args[0]
                conversation = call_args[2]

                assert len(conversation) == 1
                assert conversation[0]["type"] == "tool_use"
                assert "error" in conversation[0]
                assert conversation[0]["error"] == "Command not found"

    def test_hook_handles_missing_ticket_id(self):
        """Should handle gracefully when ticket_id is missing."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        # No ticket_id
        mock_context._current_ticket_id = None

        tool_event = {
            "tool_name": "bash",
            "tool_input": {"command": "ls"},
            "tool_output": "success",
        }

        with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
            # Should not crash
            post_tool_use_hook(context=mock_context, tool_event=tool_event)

            # Should not have saved to Notion
            assert not mock_save.called

    def test_hook_adds_timestamp_to_tool_use(self):
        """Should add timestamp to each tool use entry."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 1

        tool_event = {
            "tool_name": "bash",
            "tool_input": {"command": "pwd"},
            "tool_output": "/home/user",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=[]):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                call_args = mock_save.call_args[0]
                conversation = call_args[2]

                # Should have timestamp
                assert "timestamp" in conversation[0]
                # Timestamp should be ISO format
                assert "T" in conversation[0]["timestamp"]

    def test_hook_preserves_conversation_history(self):
        """Should preserve all existing conversation history."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._current_ticket_id = "test-ticket-123"
        mock_context._current_turn = 3

        existing_conv = [
            {"role": "user", "content": "Task 1", "turn": 0},
            {"role": "assistant", "content": "Response 1", "turn": 1},
            {"type": "tool_use", "tool_name": "read", "turn": 2},
        ]

        tool_event = {
            "tool_name": "write",
            "tool_input": {"file": "test.py", "content": "code"},
            "tool_output": "success",
        }

        with patch("src.hooks.post_tool_use.load_conversation_state", return_value=existing_conv):
            with patch("src.hooks.post_tool_use.save_conversation_state") as mock_save:
                post_tool_use_hook(context=mock_context, tool_event=tool_event)

                call_args = mock_save.call_args[0]
                conversation = call_args[2]

                # Should have all 4 entries
                assert len(conversation) == 4
                assert conversation[0]["content"] == "Task 1"
                assert conversation[1]["content"] == "Response 1"
                assert conversation[2]["tool_name"] == "read"
                assert conversation[3]["tool_name"] == "write"
