"""
Tests for UserPromptSubmit hook.
Tests written BEFORE implementation (TDD approach).

This hook handles when the agent needs user input:
- Updates Notion ticket status to "Requesting User Input"
- Saves the question to Notion conversation
- Waits for/returns user response (via WebSocket in production)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from src.hooks.user_prompt import user_prompt_submit_hook


class TestUserPromptSubmitHook:
    """Tests for user prompt submission hook."""

    def test_hook_updates_status_to_requesting_input(self):
        """Should update Notion ticket status to 'Requesting User Input'."""
        # Mock the notion client and required functions
        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        # Create a mock context with required attributes
        mock_context = Mock()
        mock_context._notion_client = mock_client
        mock_context._current_ticket_id = mock_ticket_id
        mock_context._notion_db_id = "test-db-id"
        mock_context._current_turn = 0  # Set actual value, not Mock

        with patch("src.hooks.user_prompt.update_ticket_status") as mock_update:
            with patch("src.hooks.user_prompt.load_conversation_state", return_value=[]):
                with patch("src.hooks.user_prompt.save_conversation_state"):
                    with patch("src.hooks.user_prompt.wait_for_user_response", return_value=None):
                        # Call the hook
                        result = user_prompt_submit_hook(
                            context=mock_context,
                            prompt="What is your name?"
                        )

                        # Should have updated status to "Requesting User Input"
                        # Note: It's called twice (requesting -> working)
                        calls = mock_update.call_args_list
                        assert len(calls) >= 1
                        assert calls[0][0][2] == "Requesting User Input"

    def test_hook_saves_question_to_conversation(self):
        """Should save the user prompt question to Notion conversation."""
        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        mock_context = Mock()
        mock_context._notion_client = mock_client
        mock_context._current_ticket_id = mock_ticket_id
        mock_context._notion_db_id = "test-db-id"
        mock_context._current_turn = 1

        question = "What is your favorite color?"

        with patch("src.hooks.user_prompt.update_ticket_status"):
            with patch("src.hooks.user_prompt.load_conversation_state", return_value=[]):
                with patch("src.hooks.user_prompt.save_conversation_state") as mock_save:
                    with patch("src.hooks.user_prompt.wait_for_user_response", return_value=None):
                        # Call the hook
                        result = user_prompt_submit_hook(
                            context=mock_context,
                            prompt=question
                        )

                        # Should have saved conversation
                        mock_save.assert_called_once()
                        call_args = mock_save.call_args

                        # Check that question was included in conversation
                        conversation_data = call_args[0][2]  # Third positional arg
                        assert len(conversation_data) == 1
                        assert "agent_question" in conversation_data[0]
                        assert conversation_data[0]["agent_question"] == question

    def test_hook_returns_user_input(self):
        """Should return user input response."""
        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        mock_context = Mock()
        mock_context._notion_client = mock_client
        mock_context._current_ticket_id = mock_ticket_id
        mock_context._notion_db_id = "test-db-id"
        mock_context._current_turn = 1

        # Mock the response retrieval function
        with patch("src.hooks.user_prompt.update_ticket_status"):
            with patch("src.hooks.user_prompt.save_conversation_state"):
                with patch("src.hooks.user_prompt.wait_for_user_response") as mock_wait:
                    mock_wait.return_value = "Blue"

                    # Call the hook
                    result = user_prompt_submit_hook(
                        context=mock_context,
                        prompt="What is your favorite color?"
                    )

                    # Should return the user's response
                    assert result == "Blue"
                    mock_wait.assert_called_once()

    def test_hook_handles_missing_ticket_id(self):
        """Should handle gracefully when ticket_id is missing from context."""
        mock_context = Mock()
        mock_context._notion_client = Mock()
        mock_context._notion_db_id = "test-db-id"
        # No _current_ticket_id attribute
        delattr(mock_context, '_current_ticket_id')

        with patch("src.hooks.user_prompt.update_ticket_status"):
            with patch("src.hooks.user_prompt.save_conversation_state"):
                # Should not raise an exception
                result = user_prompt_submit_hook(
                    context=mock_context,
                    prompt="Test question"
                )

                # Should return some default response or raise gracefully
                assert result is not None or result == ""

    def test_hook_increments_turn_count(self):
        """Should increment turn count when saving conversation."""
        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        mock_context = Mock()
        mock_context._notion_client = mock_client
        mock_context._current_ticket_id = mock_ticket_id
        mock_context._notion_db_id = "test-db-id"
        mock_context._current_turn = 5

        with patch("src.hooks.user_prompt.update_ticket_status"):
            with patch("src.hooks.user_prompt.save_conversation_state") as mock_save:
                with patch("src.hooks.user_prompt.wait_for_user_response", return_value="Response"):
                    # Call the hook
                    user_prompt_submit_hook(
                        context=mock_context,
                        prompt="Question?"
                    )

                    # Check that context's turn was incremented
                    assert mock_context._current_turn == 6

    def test_hook_updates_status_back_to_working_after_response(self):
        """Should update status back to 'Agent Working' after receiving user response."""
        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        mock_context = Mock()
        mock_context._notion_client = mock_client
        mock_context._current_ticket_id = mock_ticket_id
        mock_context._notion_db_id = "test-db-id"
        mock_context._current_turn = 1

        with patch("src.hooks.user_prompt.update_ticket_status") as mock_update:
            with patch("src.hooks.user_prompt.save_conversation_state"):
                with patch("src.hooks.user_prompt.wait_for_user_response", return_value="Answer"):
                    # Call the hook
                    user_prompt_submit_hook(
                        context=mock_context,
                        prompt="Question?"
                    )

                    # Should have updated status twice: requesting -> working
                    assert mock_update.call_count == 2
                    calls = mock_update.call_args_list

                    # First call: Requesting User Input
                    assert calls[0][0][2] == "Requesting User Input"
                    # Second call: Agent Working
                    assert calls[1][0][2] == "Agent Working"


class TestWaitForUserResponse:
    """Tests for the wait_for_user_response helper function."""

    def test_wait_polls_notion_for_response(self):
        """Should poll Notion for user response."""
        from src.hooks.user_prompt import wait_for_user_response

        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        # Mock Notion API to return response property
        mock_page = {
            "properties": {
                "User Response": {
                    "rich_text": [{"plain_text": "Test response"}]
                }
            }
        }
        mock_client.pages.retrieve.return_value = mock_page

        result = wait_for_user_response(mock_client, mock_ticket_id, timeout=1)

        # Should have retrieved the page
        mock_client.pages.retrieve.assert_called()
        assert result == "Test response"

    def test_wait_times_out_gracefully(self):
        """Should return None or empty string if timeout is reached."""
        from src.hooks.user_prompt import wait_for_user_response

        mock_client = Mock()
        mock_ticket_id = "test-ticket-123"

        # Mock Notion to never return a response
        mock_page = {
            "properties": {
                "User Response": {
                    "rich_text": []
                }
            }
        }
        mock_client.pages.retrieve.return_value = mock_page

        result = wait_for_user_response(mock_client, mock_ticket_id, timeout=0.1)

        # Should timeout and return empty/None
        assert result is None or result == ""
