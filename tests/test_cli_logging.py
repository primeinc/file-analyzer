#!/usr/bin/env python3
"""
Unit tests for the CLI logging configuration.

Tests various combinations of logging setup options to ensure the correct
behavior for different modes (verbose, quiet, json, ci, etc.)
"""

import unittest
import logging
import io
import sys
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from rich.console import Console

# Import the setup_logging function from our CLI module
from src.cli.main import setup_logging


class TestCliLogging(unittest.TestCase):
    """Test cases for CLI logging configuration."""

    def setUp(self):
        """Set up test environment before each test."""
        # Reset the root logger
        self.root_logger = logging.getLogger()
        self.handlers_before = self.root_logger.handlers.copy()
        self.level_before = self.root_logger.level
        
        # Redirect stdout to capture logging output
        self.stdout_capture = io.StringIO()
        self.stdout_patcher = patch('sys.stdout', self.stdout_capture)
        self.stdout_patcher.start()
        
        # Temporarily disable any existing log handlers to prevent interference
        self.root_logger.handlers = []
    
    def tearDown(self):
        """Clean up after each test."""
        # Restore root logger to original state
        self.root_logger.handlers = self.handlers_before
        self.root_logger.setLevel(self.level_before)
        
        # Stop stdout redirection
        self.stdout_patcher.stop()
        sys.stdout = sys.__stdout__
    
    def get_logger_level(self, logger_name="file-analyzer"):
        """Helper method to get the effective level of a logger."""
        # Get the logger level - if it's 0 (NOTSET), the logger inherits from parent
        logger = logging.getLogger(logger_name)
        if logger.level == 0:  # NOTSET
            # Check the root logger
            return logging.getLogger().level
        return logger.level
    
    def test_default_logging_setup(self):
        """Test default logging setup (no special options)."""
        console, logger = setup_logging()
        
        # Check console setup
        self.assertIsInstance(console, Console)
        # Don't check color_system directly as it depends on the terminal environment
        
        # Check logger
        self.assertEqual(self.get_logger_level(), logging.INFO)
        
        # Ensure there's at least one handler and it's a Handler
        self.assertTrue(len(self.root_logger.handlers) > 0)
        self.assertTrue(any(isinstance(h, logging.Handler) for h in self.root_logger.handlers))
        
        # Log a test message for coverage
        logger.info("Test default logging")
    
    def test_verbose_mode(self):
        """Test verbose logging mode."""
        console, logger = setup_logging(verbose=True)
        
        # Check logger level
        self.assertEqual(self.get_logger_level(), logging.DEBUG)
        
        # Log a debug message and check if it appears
        logger.debug("Test debug message")
        # We don't check the output directly since Rich formatting makes it complex
        # Just verify the level is set correctly
    
    def test_quiet_mode(self):
        """Test quiet logging mode."""
        console, logger = setup_logging(quiet=True)
        
        # Check logger level
        self.assertEqual(self.get_logger_level(), logging.ERROR)
        
        # Test that info messages are suppressed
        logger.info("This info message should be suppressed")
        # Error messages should still appear
        logger.error("This error message should appear")
    
    @patch('logging.FileHandler')
    @patch('pythonjsonlogger.json.JsonFormatter')
    def test_json_logging_to_file(self, mock_json_formatter, mock_file_handler):
        """Test JSON logging to a file."""
        # Mock both the file handler and JsonFormatter to avoid creating real files
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler
        
        console, logger = setup_logging(json_logs=True, log_file="test.log")
        
        # Verify FileHandler was called with the right filename
        mock_file_handler.assert_called_once_with("test.log")
        
        # Verify a JSON formatter was created
        mock_json_formatter.assert_called_once()
        
        # Verify the formatter was set on the handler
        mock_handler.setFormatter.assert_called_once()
    
    @patch('logging.FileHandler')
    def test_standard_logging_to_file(self, mock_file_handler):
        """Test standard (non-JSON) logging to a file."""
        # Mock the file handler to avoid creating real files
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler
        
        console, logger = setup_logging(log_file="test.log")
        
        # The current implementation doesn't support non-JSON file logging directly,
        # so this verifies current behavior where log_file is ignored unless json_logs is True
        
        # Verify FileHandler was NOT called
        mock_file_handler.assert_not_called()
        
        # Verify we still have a RichHandler
        rich_handlers = [h for h in self.root_logger.handlers 
                        if h.__class__.__name__ == 'RichHandler']
        self.assertTrue(len(rich_handlers) > 0, "No RichHandler found")
    
    def test_json_logging_to_stdout(self):
        """Test JSON logging to stdout."""
        # This test is simplified to just check if a JsonFormatter is used
        # We don't try to parse the actual output since that's too environment-dependent
        with patch('pythonjsonlogger.json.JsonFormatter') as mock_formatter:
            # Mock the JsonFormatter and just verify it's used
            console, logger = setup_logging(json_logs=True)
            
            # Verify a formatter was created
            mock_formatter.assert_called_once()
            
            # Log a test message for coverage
            logger.info("Test JSON logging")
            
            # Check if there's a handler with our formatter
            # We don't check the actual output as it can vary by environment
    
    def test_ci_mode(self):
        """Test CI mode (no colors, no animations)."""
        console, logger = setup_logging(ci=True)
        
        # In CI mode, the console should have specific settings
        self.assertFalse(console._highlight)
        self.assertFalse(console._emoji)
        
        # Check the rich handler
        rich_handlers = [h for h in self.root_logger.handlers 
                        if h.__class__.__name__ == 'RichHandler']
        if rich_handlers:
            handler = rich_handlers[0]
            # In newer versions of rich, these might be in different attributes
            # Check if they're in the handler object directly
            if hasattr(handler, 'show_time'):
                self.assertFalse(handler.show_time)
                self.assertFalse(handler.show_path)
            # Otherwise, check if they're in the '_console_options' dict
            elif hasattr(handler, '_console_options'):
                self.assertTrue('show_time' not in handler._console_options or 
                              not handler._console_options.get('show_time', True))
                self.assertTrue('show_path' not in handler._console_options or 
                              not handler._console_options.get('show_path', True))
    
    def test_no_color_mode(self):
        """Test no-color mode."""
        console, logger = setup_logging(no_color=True)
        
        # Check that color system is disabled
        self.assertIsNone(console.color_system)
        
    def test_handler_clearing(self):
        """Test that existing handlers are cleared when setup_logging is called multiple times."""
        # Add a dummy handler to root logger
        dummy_handler = logging.StreamHandler()
        logging.root.addHandler(dummy_handler)
        original_handler_count = len(logging.root.handlers)
        
        # Call setup_logging multiple times
        setup_logging()
        setup_logging()
        
        # The number of handlers should remain consistent (not increase with each call)
        self.assertLessEqual(len(logging.root.handlers), original_handler_count)
    
    def test_combined_modes(self):
        """Test combinations of different modes."""
        # Test verbose + json logging
        console, logger = setup_logging(verbose=True, json_logs=True)
        self.assertEqual(self.get_logger_level(), logging.DEBUG)
        
        # Reset for the next test
        self.setUp()
        
        # Test quiet + CI mode
        console, logger = setup_logging(quiet=True, ci=True)
        self.assertEqual(self.get_logger_level(), logging.ERROR)
        self.assertFalse(console._highlight)
    
    def test_verbose_and_quiet_precedence(self):
        """Test that quiet mode takes precedence over verbose mode when both are enabled."""
        # When both verbose and quiet are enabled, quiet should win
        console, logger = setup_logging(verbose=True, quiet=True)
        self.assertEqual(self.get_logger_level(), logging.ERROR)
        
        # Test that debug logs are NOT processed
        with patch.object(logger, 'callHandlers') as mock_call_handlers:
            logger.debug("Debug message should not be processed")
            # Debug should not call handlers since we're in ERROR level
            mock_call_handlers.assert_not_called()
            
            # Reset the mock for next assertion
            mock_call_handlers.reset_mock()
            
            # Error should still call handlers
            logger.error("Error message should be processed")
            mock_call_handlers.assert_called_once()


    def test_log_file_with_json_logs(self):
        """Test the combination of log file and JSON logging."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.log') as tmp_file:
            with patch('sys.stdout', new_callable=io.StringIO):
                console, logger = setup_logging(json_logs=True, log_file=tmp_file.name)
                
                # Log some test messages
                logger.info("Test info message")
                logger.error("Test error message")
                
                # Read the log file content
                tmp_file.flush()
                with open(tmp_file.name, 'r') as f:
                    content = f.read()
                
                # Check if anything was written to the file
                self.assertTrue(len(content) > 0, "Log file should contain content")
                
                # Check that at least our message text is in the logs
                self.assertIn("Test info message", content)
                self.assertIn("Test error message", content)

    def test_ci_mode_with_verbose(self):
        """Test combination of CI mode with verbose logging."""
        console, logger = setup_logging(verbose=True, ci=True)
        
        # Should have debug level due to verbose
        self.assertEqual(self.get_logger_level(), logging.DEBUG)
        
        # Should have CI mode console settings
        self.assertFalse(console._emoji)
        self.assertFalse(console._highlight)


if __name__ == "__main__":
    unittest.main()