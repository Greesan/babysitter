"""
Tests for Agent SDK runner.
Tests written BEFORE implementation (TDD approach).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.agent import (
    initialize_agent,
    run_agent_for_ticket,
    AgentConfig,
)


class TestAgentInitialization:
    """Tests for agent initialization and configuration."""

    def test_agent_config_has_required_fields(self):
        """Should have all required configuration fields."""
        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id",
            model="sonnet"
        )

        assert config.notion_token == "test_token"
        assert config.notion_db_id == "test_db_id"
        assert config.model == "sonnet"

    def test_agent_config_has_sensible_defaults(self):
        """Should provide sensible defaults for optional fields."""
        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        # Default model should be specified
        assert hasattr(config, "model")
        assert config.model == "sonnet"
        # Default timeout/max_turns should be reasonable
        assert hasattr(config, "max_turns")
        assert config.max_turns == 50

    @patch("src.agent.Client")
    @patch("src.agent.ClaudeSDKClient")
    def test_initialize_agent_returns_client(self, mock_sdk, mock_notion):
        """Should return configured Claude SDK client."""
        mock_sdk.return_value = MagicMock()
        mock_notion.return_value = MagicMock()

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        client = initialize_agent(config)

        # Should return a client-like object
        assert client is not None
        # Should have initialized the SDK client
        mock_sdk.assert_called_once()


class TestAgentTicketProcessing:
    """Tests for processing tickets with the agent."""

    @pytest.mark.asyncio
    @patch("src.agent.Client")
    @patch("src.agent.get_ticket_context")
    @patch("src.agent.update_ticket_status")
    @patch("src.agent.claim_pending_ticket")
    @patch("src.agent.initialize_agent")
    async def test_run_agent_claims_pending_ticket(
        self, mock_init, mock_claim, mock_status, mock_context, mock_client_class
    ):
        """Should claim a pending ticket before starting agent."""
        mock_claim.return_value = {
            "ticket_id": "test-ticket-123",
            "session_id": "session-456",
            "ticket_name": "Test Task"
        }
        mock_context.return_value = {
            "ticket_name": "Test Task",
            "status": "Agent Planning",
            "session_id": "session-456",
            "conversation": [],
            "turn_count": 0
        }
        mock_client = Mock()
        mock_client.query = AsyncMock()  # Mock the async query method
        mock_init.return_value = mock_client

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        result = await run_agent_for_ticket(config)

        # Should have called claim_pending_ticket
        assert mock_claim.call_count == 1
        assert result is not None

    @pytest.mark.asyncio
    @patch("src.agent.Client")
    @patch("src.agent.claim_pending_ticket")
    async def test_run_agent_returns_none_when_no_tickets(self, mock_claim, mock_client_class):
        """Should return None if no pending tickets exist."""
        mock_claim.return_value = None

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        result = await run_agent_for_ticket(config)

        assert result is None

    @pytest.mark.asyncio
    @patch("src.agent.Client")
    @patch("src.agent.get_ticket_context")
    @patch("src.agent.update_ticket_status")
    @patch("src.agent.claim_pending_ticket")
    @patch("src.agent.initialize_agent")
    async def test_run_agent_loads_ticket_context(
        self, mock_init, mock_claim, mock_status, mock_context, mock_client_class
    ):
        """Should load ticket context after claiming."""
        mock_claim.return_value = {
            "ticket_id": "test-ticket-123",
            "session_id": "session-456",
            "ticket_name": "Test Task"
        }
        mock_context.return_value = {
            "ticket_name": "Test Task",
            "status": "Agent Planning",
            "session_id": "session-456",
            "conversation": [],
            "turn_count": 0
        }
        mock_client = Mock()
        mock_client.query = AsyncMock()
        mock_init.return_value = mock_client

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        result = await run_agent_for_ticket(config)

        # Should have loaded context
        assert mock_context.call_count == 1
        call_args = mock_context.call_args[0]
        assert call_args[1] == "test-ticket-123"  # ticket_id


class TestAgentConversationFlow:
    """Tests for agent conversation management."""

    @pytest.mark.asyncio
    @patch("src.agent.Client")
    @patch("src.agent.get_ticket_context")
    @patch("src.agent.session_start_hook")
    @patch("src.agent.claim_pending_ticket")
    @patch("src.agent.initialize_agent")
    async def test_run_agent_updates_status_to_working(
        self, mock_init, mock_claim, mock_session_hook, mock_context, mock_client_class
    ):
        """Should call session_start_hook which updates status to 'Agent Working'."""
        mock_claim.return_value = {
            "ticket_id": "test-ticket-123",
            "session_id": "session-456",
            "ticket_name": "Test Task"
        }
        mock_context.return_value = {
            "ticket_name": "Test Task",
            "status": "Agent Planning",
            "session_id": "session-456",
            "conversation": [],
            "turn_count": 0
        }
        mock_client = Mock()
        mock_client.query = AsyncMock()
        mock_init.return_value = mock_client
        mock_session_hook.return_value = []  # Empty conversation

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        await run_agent_for_ticket(config)

        # Should have called session_start_hook (which updates status to "Agent Working")
        assert mock_session_hook.call_count == 1

    @pytest.mark.asyncio
    @patch("src.agent.Client")
    @patch("src.agent.get_ticket_context")
    @patch("src.agent.session_start_hook")
    @patch("src.agent.claim_pending_ticket")
    @patch("src.agent.initialize_agent")
    async def test_run_agent_creates_initial_prompt_from_ticket(
        self, mock_init, mock_claim, mock_session_hook, mock_context, mock_client_class
    ):
        """Should create initial prompt from ticket name."""
        mock_claim.return_value = {
            "ticket_id": "test-ticket-123",
            "session_id": "session-456",
            "ticket_name": "Fix the login bug"
        }
        mock_context.return_value = {
            "ticket_name": "Fix the login bug",
            "status": "Agent Planning",
            "session_id": "session-456",
            "conversation": [],
            "turn_count": 0
        }
        mock_client = Mock()
        mock_client.query = AsyncMock()
        mock_init.return_value = mock_client
        mock_session_hook.return_value = []  # Empty conversation

        config = AgentConfig(
            notion_token="test_token",
            notion_db_id="test_db_id"
        )

        result = await run_agent_for_ticket(config)

        # Should have some result indicating agent was started
        assert result is not None
        assert result["ticket_name"] == "Fix the login bug"
        assert result["status"] == "completed"  # Changed from "initialized" since agent actually runs now
