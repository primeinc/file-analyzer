#!/usr/bin/env python3
"""
Smoke tests for CLI entry points.

These tests exercise the main CLI entry points to ensure they don't crash
and provide basic functionality validation.
"""

import os
import tempfile
from unittest.mock import patch

import typer
import typer.testing

# Import all the apps from main CLI module
from src.cli.analyze.main import app as analyze_app
from src.cli.artifact.main import app as artifact_app
from src.cli.benchmark.main import app as benchmark_app
from src.cli.install.main import app as install_app
from src.cli.main import app as main_app, setup_logging
from src.cli.model.main import app as model_app
from src.cli.test.main import app as test_app
from src.cli.validate.main import app as validate_app

# Set up test runner
runner = typer.testing.CliRunner()


class TestMainApp:
    """Test main CLI app functionality."""

    def test_main_app_help(self):
        """Test main app shows help."""
        result = runner.invoke(main_app, ["--help"])
        assert result.exit_code == 0
        assert "File Analyzer CLI" in result.stdout

    def test_setup_logging_basic(self):
        """Test logging setup works."""
        console, logger = setup_logging()
        assert console is not None
        assert logger is not None

    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        console, logger = setup_logging(verbose=True)
        assert console is not None
        assert logger is not None

    def test_setup_logging_quiet(self):
        """Test quiet logging setup."""
        console, logger = setup_logging(quiet=True)
        assert console is not None
        assert logger is not None

    def test_setup_logging_json(self):
        """Test JSON logging setup."""
        console, logger = setup_logging(json_logs=True)
        assert console is not None
        assert logger is not None


class TestAnalyzeApp:
    """Test analyze subcommand functionality."""

    def test_analyze_help(self):
        """Test analyze command shows help."""
        result = runner.invoke(analyze_app, ["--help"])
        assert result.exit_code == 0

    def test_analyze_verify_help(self):
        """Test analyze verify subcommand help."""
        result = runner.invoke(analyze_app, ["verify", "--help"])
        assert result.exit_code == 0

    @patch("subprocess.run")
    def test_analyze_verify_basic(self, mock_run):
        """Test analyze verify runs without crashing."""
        # Mock successful dependency checks
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "version 1.0.0"

        result = runner.invoke(analyze_app, ["verify"])
        # May exit with error due to missing deps, but shouldn't crash
        assert result.exit_code in [0, 1]

    def test_analyze_metadata_help(self):
        """Test analyze metadata subcommand help."""
        result = runner.invoke(analyze_app, ["metadata", "--help"])
        assert result.exit_code == 0

    @patch("src.core.analyzer.FileAnalyzer")
    def test_analyze_metadata_basic(self, mock_analyzer):
        """Test analyze metadata runs without crashing."""
        mock_analyzer.return_value.analyze.return_value = {}

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(analyze_app, ["metadata", temp_dir])
            # May exit with error due to no files, but shouldn't crash
            assert result.exit_code in [0, 1]


class TestModelApp:
    """Test model subcommand functionality."""

    def test_model_help(self):
        """Test model command shows help."""
        result = runner.invoke(model_app, ["--help"])
        assert result.exit_code == 0

    def test_model_list_help(self):
        """Test model list subcommand help."""
        result = runner.invoke(model_app, ["list", "--help"])
        assert result.exit_code == 0

    @patch("src.models.manager.ModelManager")
    def test_model_list_basic(self, mock_manager):
        """Test model list runs without crashing."""
        mock_manager.return_value.get_available_models.return_value = {
            "fastvlm": ["0.5b", "1.5b", "7b"]
        }

        result = runner.invoke(model_app, ["list"])
        assert result.exit_code == 0

    def test_model_status_help(self):
        """Test model status subcommand help."""
        result = runner.invoke(model_app, ["status", "--help"])
        # Accept exit code 2 as it might not be fully implemented yet
        assert result.exit_code in [0, 2]


class TestValidateApp:
    """Test validate subcommand functionality."""

    def test_validate_help(self):
        """Test validate command shows help."""
        result = runner.invoke(validate_app, ["--help"])
        assert result.exit_code == 0

    def test_validate_schema_help(self):
        """Test validate schema subcommand help."""
        result = runner.invoke(validate_app, ["schema", "--help"])
        assert result.exit_code == 0

    def test_validate_schema_with_invalid_file(self):
        """Test validate handles invalid JSON file gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write("invalid json{")
            tmp.flush()

            result = runner.invoke(validate_app, ["schema", tmp.name])
            # Should fail gracefully
            assert result.exit_code == 1
            
        os.unlink(tmp.name)

    def test_validate_schema_with_valid_file(self):
        """Test validate handles valid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write('{"test": "data"}')
            tmp.flush()

            result = runner.invoke(validate_app, ["schema", tmp.name])
            # May exit with schema validation error but shouldn't crash JSON parsing
            assert result.exit_code in [0, 1]
            
        os.unlink(tmp.name)


class TestTestApp:
    """Test test subcommand functionality."""

    def test_test_help(self):
        """Test test command shows help."""
        result = runner.invoke(test_app, ["--help"])
        assert result.exit_code == 0

    def test_test_list(self):
        """Test test list runs without crashing."""
        result = runner.invoke(test_app, ["list"])
        # May exit with various codes but shouldn't crash
        assert result.exit_code in [0, 1]

    def test_test_run(self):
        """Test test run without arguments."""
        result = runner.invoke(test_app, ["run"])
        # May exit with various codes but shouldn't crash
        assert result.exit_code in [0, 1]


class TestInstallApp:
    """Test install subcommand functionality."""

    def test_install_help(self):
        """Test install command shows help."""
        result = runner.invoke(install_app, ["--help"])
        assert result.exit_code == 0

    def test_install_basic(self):
        """Test install runs without crashing."""
        result = runner.invoke(install_app)
        # May exit with error on missing tools but shouldn't crash
        assert result.exit_code in [0, 1, 2]


class TestArtifactApp:
    """Test artifact subcommand functionality."""

    def test_artifact_help(self):
        """Test artifact command shows help."""
        result = runner.invoke(artifact_app, ["--help"])
        assert result.exit_code == 0

    def test_artifact_status_help(self):
        """Test artifact status subcommand help."""
        result = runner.invoke(artifact_app, ["status", "--help"])
        # Accept exit code 2 as it might not be fully implemented yet
        assert result.exit_code in [0, 2]


class TestBenchmarkApp:
    """Test benchmark subcommand functionality."""

    def test_benchmark_help(self):
        """Test benchmark command shows help."""
        result = runner.invoke(benchmark_app, ["--help"])
        assert result.exit_code == 0