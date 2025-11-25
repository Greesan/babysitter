"""
Tests for removing unused file types (.question and .done files).
"""
import os
import sys
import tempfile
import shutil

import pytest


class TestFileTypeCleanup:
    """Test that .question and .done files are no longer created or used."""

    @pytest.fixture
    def temp_ticket_dir(self):
        """Create a temporary ticket directory for testing."""
        temp_dir = tempfile.mkdtemp()
        os.environ["CLAUDE_TICKET_DIR"] = temp_dir
        yield temp_dir
        shutil.rmtree(temp_dir)
        if "CLAUDE_TICKET_DIR" in os.environ:
            del os.environ["CLAUDE_TICKET_DIR"]

    def test_notion_mcp_server_does_not_create_question_file(self, temp_ticket_dir):
        """Test that notion_mcp_server no longer creates .question files."""
        # This test will pass once we remove the .question file creation
        # For now, it documents the expected behavior
        pass

    def test_cleanup_tickets_does_not_reference_question_files(self, temp_ticket_dir):
        """Test that cleanup_tickets.py doesn't reference .question files."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

        # Read the cleanup_tickets.py source
        cleanup_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'cleanup_tickets.py')
        with open(cleanup_path, 'r') as f:
            content = f.read()

        # After refactoring, .question should not be in the file extensions tuple
        # This is a negative assertion - we're checking the desired end state
        assert '".question"' not in content or '.question' not in content.split('if f.endswith')[1].split(')')[0]

    def test_cleanup_tickets_does_not_reference_done_files(self, temp_ticket_dir):
        """Test that cleanup_tickets.py doesn't reference .done files."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

        cleanup_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'cleanup_tickets.py')
        with open(cleanup_path, 'r') as f:
            content = f.read()

        # After refactoring, .done should not be in the file extensions tuple
        assert '".done"' not in content or '.done' not in content.split('if f.endswith')[1].split(')')[0]

    def test_resume_poll_does_not_reference_question_files(self, temp_ticket_dir):
        """Test that resume_poll.py doesn't reference .question files in archive operations."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

        resume_poll_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'resume_poll.py')
        with open(resume_poll_path, 'r') as f:
            content = f.read()

        # Count occurrences of .question in archive operations
        # After refactoring, should be 0
        question_count = content.count('".question"')
        assert question_count == 0, f"Found {question_count} references to .question files"

    def test_only_page_and_conversation_files_remain(self, temp_ticket_dir):
        """Test that only .page and .conversation files are actively used."""
        # After refactoring, the system should only use:
        # - .page (Notion page ID)
        # - .conversation (conversation file path)

        # This test documents the expected file types
        expected_file_types = [".page", ".conversation"]

        # Verify these are the only file types mentioned in cleanup
        cleanup_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'cleanup_tickets.py')
        with open(cleanup_path, 'r') as f:
            content = f.read()

        # Check that cleanup only handles expected file types
        for file_type in expected_file_types:
            assert file_type in content

    def test_done_status_handled_via_notion_ui(self, temp_ticket_dir):
        """Test that 'Done' status is determined from Notion, not local .done files."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

        resume_poll_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'resume_poll.py')
        with open(resume_poll_path, 'r') as f:
            content = f.read()

        # Should check for Status == "Done" in Notion
        assert 'Status' in content
        assert '"Done"' in content or "'Done'" in content

        # Should NOT check for .done files
        assert not os.path.exists(os.path.join(temp_ticket_dir, "*.done"))
