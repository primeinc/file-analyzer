#!/usr/bin/env python3
"""
Unit tests for CLI entry point and plugin loading

Tests the main CLI module's initialization, plugin discovery, and basic functionality.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from importlib import metadata

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import module to test
from src.cli.main import app, load_commands, _import_builtin_commands, capture_environment


class TestCLIEntryPoint(unittest.TestCase):
    """Test cases for CLI entry point and plugin loading."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset sys.modules cache for modules that will be mocked
        modules_to_reset = [
            'src.cli.analyze.main', 
            'src.cli.test.hook',  # Note: changed from test.main to test.hook
            'src.cli.validate.main',
            'src.cli.artifact.main',
            'src.cli.artifact.preflight',
            'src.cli.artifact.adapter',
            'src.cli.install.main',
            'src.cli.model.main',
            'src.cli.benchmark.main'
        ]
        for module in modules_to_reset:
            if module in sys.modules:
                del sys.modules[module]
    
    @patch('typer.Typer.add_typer')
    def test_import_builtin_commands(self, mock_add_typer):
        """Test direct import of builtin commands."""
        # The refactored code now has 8 commands instead of 3
        # Mock the apps for all commands
        analyze_app_mock = MagicMock()
        test_app_mock = MagicMock()
        validate_app_mock = MagicMock()
        artifact_app_mock = MagicMock()
        preflight_app_mock = MagicMock()
        install_app_mock = MagicMock()
        model_app_mock = MagicMock()
        benchmark_app_mock = MagicMock()
        
        # Mock the imports
        with patch.dict('sys.modules', {
            'src.cli.analyze.main': MagicMock(app=analyze_app_mock),
            'src.cli.test.hook': MagicMock(app=test_app_mock),
            'src.cli.validate.main': MagicMock(app=validate_app_mock),
            'src.cli.artifact.main': MagicMock(app=artifact_app_mock),
            'src.cli.artifact.preflight': MagicMock(app=preflight_app_mock),
            'src.cli.artifact.adapter': MagicMock(),
            'src.cli.install.main': MagicMock(app=install_app_mock),
            'src.cli.model.main': MagicMock(app=model_app_mock),
            'src.cli.benchmark.main': MagicMock(app=benchmark_app_mock)
        }):
            # Call the function
            _import_builtin_commands()
            
            # Check that add_typer was called for each command (8 regular commands + 0 module imports)
            # The adapter command is imported as a module, so it doesn't call add_typer
            self.assertEqual(mock_add_typer.call_count, 8)
            
            # Verify the calls for a few key commands
            mock_add_typer.assert_any_call(analyze_app_mock, name="analyze")
            mock_add_typer.assert_any_call(test_app_mock, name="test")
            mock_add_typer.assert_any_call(validate_app_mock, name="validate")
            mock_add_typer.assert_any_call(artifact_app_mock, name="artifact")
    
    @patch('src.cli.main.entry_points')
    @patch('importlib.import_module')
    @patch('typer.Typer.add_typer')
    def test_load_commands_via_entry_points(self, mock_add_typer, mock_import_module, mock_entry_points):
        """Test loading commands via entry points."""
        # The refactored load_commands function uses command_mapping to determine
        # which modules to load, even when entry points are available
        
        # Create mock modules that will be imported
        mock_analyze = MagicMock()
        mock_analyze.app = MagicMock()
        
        mock_test = MagicMock()
        mock_test.app = MagicMock()
        
        # Set up the return value for import_module
        mock_import_module.side_effect = lambda module_path: {
            'src.cli.analyze.main': mock_analyze,
            'src.cli.test.hook': mock_test,
        }.get(module_path, MagicMock())
        
        # Create mock entry points with matching names from command_mapping
        mock_entry1 = MagicMock()
        mock_entry1.name = "analyze"
        
        mock_entry2 = MagicMock()
        mock_entry2.name = "test"
        
        # Set up the entry_points return value
        mock_entry_points.return_value = [mock_entry1, mock_entry2]
        
        # Call the function
        load_commands()
        
        # Check that entry_points was called with the right group
        mock_entry_points.assert_called_once_with(group='fa.commands')
        
        # Check that add_typer was called at least once for each entry point that matched
        # Since the implementation now uses importlib.import_module instead of entry.load(),
        # we check that the right modules were imported
        mock_import_module.assert_any_call('src.cli.analyze.main')
        mock_import_module.assert_any_call('src.cli.test.hook')
        
        # Check that add_typer was called with the apps from our mock modules
        self.assertGreaterEqual(mock_add_typer.call_count, 2)
        mock_add_typer.assert_any_call(mock_analyze.app, name="analyze")
        mock_add_typer.assert_any_call(mock_test.app, name="test")
    
    @patch('src.cli.main.entry_points')
    @patch('src.cli.main._import_builtin_commands')
    def test_load_commands_fallback(self, mock_import_builtin, mock_entry_points):
        """Test fallback to direct imports if entry points discovery fails."""
        # Make entry_points raise an exception
        mock_entry_points.side_effect = Exception("Entry points discovery failed")
        
        # Call the function
        load_commands()
        
        # Check that _import_builtin_commands was called
        mock_import_builtin.assert_called_once()
    
    def test_capture_environment(self):
        """Test environment capture function."""
        env = capture_environment()
        
        # Check that required keys are present
        self.assertIn('python_version', env)
        self.assertIn('platform', env)
        self.assertIn('os_name', env)
        self.assertIn('user', env)
        self.assertIn('pwd', env)
        
        # Check that values are of expected types
        self.assertIsInstance(env['python_version'], str)
        self.assertIsInstance(env['platform'], str)
        self.assertIsInstance(env['os_name'], str)
        self.assertIsInstance(env['pwd'], str)


if __name__ == "__main__":
    unittest.main()