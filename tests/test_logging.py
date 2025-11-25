"""
Tests for logging infrastructure across all scripts.
"""
import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path

import pytest


class TestLoggingSetup:
    """Test the logging setup function."""

    @pytest.fixture
    def temp_ticket_dir(self):
        """Create a temporary ticket directory for testing."""
        temp_dir = tempfile.mkdtemp()
        os.environ["CLAUDE_TICKET_DIR"] = temp_dir
        yield temp_dir
        shutil.rmtree(temp_dir)
        if "CLAUDE_TICKET_DIR" in os.environ:
            del os.environ["CLAUDE_TICKET_DIR"]

    def test_setup_logging_creates_logger(self, temp_ticket_dir):
        """Test that setup_logging creates a logger with the correct name."""
        # Import here to use the temp_ticket_dir
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        logger = setup_logging("test_script")

        assert logger is not None
        assert logger.name == "test_script"
        assert logger.level == logging.DEBUG

    def test_setup_logging_creates_log_directory(self, temp_ticket_dir):
        """Test that setup_logging creates the logs directory."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        setup_logging("test_script")

        log_dir = os.path.join(temp_ticket_dir, "logs")
        assert os.path.exists(log_dir)
        assert os.path.isdir(log_dir)

    def test_setup_logging_creates_log_file(self, temp_ticket_dir):
        """Test that setup_logging creates a log file."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        logger = setup_logging("test_script")
        logger.info("Test message")

        log_file = os.path.join(temp_ticket_dir, "logs", "test_script.log")
        assert os.path.exists(log_file)

        # Check that the log file contains the message
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test message" in content
            assert "[INFO]" in content

    def test_setup_logging_has_console_handler(self, temp_ticket_dir):
        """Test that logger has a console (stderr) handler."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        logger = setup_logging("test_script")

        # Check for StreamHandler (console)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) > 0

        # Verify it's stderr
        assert stream_handlers[0].stream == sys.stderr

    def test_setup_logging_has_file_handler(self, temp_ticket_dir):
        """Test that logger has a rotating file handler."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging
        from logging.handlers import RotatingFileHandler

        logger = setup_logging("test_script")

        # Check for RotatingFileHandler
        file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) > 0

        # Verify max bytes and backup count
        file_handler = file_handlers[0]
        assert file_handler.maxBytes == 10*1024*1024  # 10MB
        assert file_handler.backupCount == 5

    def test_console_logs_info_and_above(self, temp_ticket_dir, caplog):
        """Test that console handler only logs INFO and above."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        logger = setup_logging("test_script")

        # Get console handler
        console_handler = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)][0]
        assert console_handler.level == logging.INFO

    def test_file_logs_debug_and_above(self, temp_ticket_dir):
        """Test that file handler logs DEBUG and above."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging
        from logging.handlers import RotatingFileHandler

        logger = setup_logging("test_script")
        logger.debug("Debug message")

        # Get file handler
        file_handler = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)][0]
        assert file_handler.level == logging.DEBUG

        # Verify debug message in file
        log_file = os.path.join(temp_ticket_dir, "logs", "test_script.log")
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Debug message" in content
            assert "[DEBUG]" in content

    def test_log_format_includes_timestamp_and_line_number(self, temp_ticket_dir):
        """Test that file log format includes timestamp and line number."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from notion_mcp_server import setup_logging

        logger = setup_logging("test_script")
        logger.info("Format test")

        log_file = os.path.join(temp_ticket_dir, "logs", "test_script.log")
        with open(log_file, 'r') as f:
            content = f.read()
            # Should contain timestamp (YYYY-MM-DD format)
            assert any(char.isdigit() for char in content)
            # Should contain level
            assert "[INFO]" in content
            # Should contain script name
            assert "test_script" in content
            # Should contain line number (:<digits>)
            assert ":" in content
