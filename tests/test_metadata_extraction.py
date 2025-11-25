"""
Tests for metadata extraction and file path validation.
"""
import os
import sys
import json
import tempfile
import shutil

import pytest


class TestMetadataExtraction:
    """Test the extract_metadata function with various scenarios."""

    @pytest.fixture
    def temp_ticket_dir(self):
        """Create a temporary ticket directory for testing."""
        temp_dir = tempfile.mkdtemp()
        os.environ["CLAUDE_TICKET_DIR"] = temp_dir
        os.environ["INCLUDE_METADATA"] = "true"
        yield temp_dir
        shutil.rmtree(temp_dir)
        if "CLAUDE_TICKET_DIR" in os.environ:
            del os.environ["CLAUDE_TICKET_DIR"]
        if "INCLUDE_METADATA" in os.environ:
            del os.environ["INCLUDE_METADATA"]

    @pytest.fixture
    def sample_conversation(self, temp_ticket_dir):
        """Create a sample conversation JSON file."""
        conv_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello, please help me"}]
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "I'll help you"},
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"}
                        },
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ls -la"}
                        }
                    ]
                }
            ]
        }

        conv_file = os.path.join(temp_ticket_dir, "conversation.json")
        with open(conv_file, 'w') as f:
            json.dump(conv_data, f)

        return conv_file

    def test_extract_metadata_returns_none_when_metadata_disabled(self, temp_ticket_dir, sample_conversation):
        """Test that extract_metadata returns None when INCLUDE_METADATA is false."""
        os.environ["INCLUDE_METADATA"] = "false"

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        result = extract_metadata(sample_conversation)
        assert result is None

    def test_extract_metadata_returns_none_when_file_missing(self, temp_ticket_dir):
        """Test that extract_metadata returns None when conversation file doesn't exist."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        missing_file = os.path.join(temp_ticket_dir, "nonexistent.json")
        result = extract_metadata(missing_file)
        assert result is None

    def test_extract_metadata_returns_none_on_invalid_json(self, temp_ticket_dir):
        """Test that extract_metadata returns None when JSON is invalid."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        invalid_json_file = os.path.join(temp_ticket_dir, "invalid.json")
        with open(invalid_json_file, 'w') as f:
            f.write("{invalid json content")

        result = extract_metadata(invalid_json_file)
        assert result is None

    def test_extract_metadata_extracts_tool_calls(self, temp_ticket_dir, sample_conversation):
        """Test that extract_metadata correctly extracts tool calls."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        result = extract_metadata(sample_conversation)

        assert result is not None
        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 2

        # Check Edit tool
        edit_tool = result["tool_calls"][0]
        assert edit_tool["name"] == "Edit"
        assert edit_tool["input"]["file_path"] == "/test/file.py"

        # Check Bash tool
        bash_tool = result["tool_calls"][1]
        assert bash_tool["name"] == "Bash"
        assert bash_tool["input"]["command"] == "ls -la"

    def test_extract_metadata_tracks_files_changed(self, temp_ticket_dir, sample_conversation):
        """Test that extract_metadata tracks files changed by Edit/Write tools."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        result = extract_metadata(sample_conversation)

        assert result is not None
        assert "files_changed" in result
        assert "/test/file.py" in result["files_changed"]

    def test_extract_metadata_tracks_commands(self, temp_ticket_dir, sample_conversation):
        """Test that extract_metadata tracks bash commands."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        result = extract_metadata(sample_conversation)

        assert result is not None
        assert "commands" in result
        assert "ls -la" in result["commands"]

    def test_extract_metadata_builds_conversation_summary(self, temp_ticket_dir, sample_conversation):
        """Test that extract_metadata builds conversation summary."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        result = extract_metadata(sample_conversation)

        assert result is not None
        assert "conversation_summary" in result
        assert len(result["conversation_summary"]) == 2

        # Check user message
        user_msg = result["conversation_summary"][0]
        assert user_msg["role"] == "user"
        assert "Hello" in user_msg["text"]

        # Check assistant message
        assistant_msg = result["conversation_summary"][1]
        assert assistant_msg["role"] == "assistant"
        assert "help you" in assistant_msg["text"]

    def test_extract_metadata_handles_empty_conversation(self, temp_ticket_dir):
        """Test that extract_metadata handles empty conversation gracefully."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata

        empty_conv = os.path.join(temp_ticket_dir, "empty.json")
        with open(empty_conv, 'w') as f:
            json.dump({"messages": []}, f)

        result = extract_metadata(empty_conv)

        assert result is not None
        assert result["tool_calls"] == []
        assert result["files_changed"] == []
        assert result["commands"] == []
        assert result["conversation_summary"] == []

    def test_extract_metadata_logs_warning_for_missing_file(self, temp_ticket_dir, caplog):
        """Test that extract_metadata logs a warning when file is missing."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata
        import logging

        with caplog.at_level(logging.WARNING):
            missing_file = os.path.join(temp_ticket_dir, "missing.json")
            extract_metadata(missing_file)

        assert any("not found" in record.message.lower() for record in caplog.records)

    def test_extract_metadata_logs_error_for_invalid_json(self, temp_ticket_dir, caplog):
        """Test that extract_metadata logs error for invalid JSON."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import extract_metadata
        import logging

        invalid_json_file = os.path.join(temp_ticket_dir, "invalid.json")
        with open(invalid_json_file, 'w') as f:
            f.write("{invalid")

        with caplog.at_level(logging.ERROR):
            extract_metadata(invalid_json_file)

        assert any("invalid json" in record.message.lower() for record in caplog.records)
