#!/usr/bin/env python3
"""
Test subcommand for the File Analyzer CLI

This module implements the 'test' subcommand, which provides a framework for
running tests on the File Analyzer components.
"""

import os
import sys
import logging
import importlib
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# Import CLI common utilities
from src.cli.common.config import config

# Create Typer app for test subcommand
app = typer.Typer(help="Run test suites and validation checks")
console = Console()

class TestRegistry:
    """
    Registry for test plugins.
    
    This class maintains a registry of test plugins and provides
    methods for registering and retrieving tests.
    """
    
    def __init__(self):
        """Initialize the test registry."""
        self.tests = {}
        self._discover_tests()
    
    def _discover_tests(self):
        """
        Discover tests from entry points and direct imports.
        """
        # Discover tests from entry points
        try:
            from importlib.metadata import entry_points
            discovered_tests = entry_points(group='fa.tests')
            
            for entry in discovered_tests:
                try:
                    test_func = entry.load()
                    self.register(entry.name, test_func)
                    logging.debug(f"Registered test from entry point: {entry.name}")
                except Exception as e:
                    logging.error(f"Failed to load test plugin '{entry.name}': {e}")
        except Exception as e:
            logging.warning(f"Error discovering test plugins: {e}")
        
        # Discover tests from direct imports in this package
        try:
            # Get the directory containing this file
            test_dir = Path(__file__).parent
            
            # Look for Python files in the directory
            for file_path in test_dir.glob("*.py"):
                if file_path.name.startswith("_") or file_path.name == "main.py":
                    continue
                
                module_name = f"src.cli.test.{file_path.stem}"
                try:
                    module = importlib.import_module(module_name)
                    
                    # Look for run_test function
                    if hasattr(module, "run_test"):
                        self.register(file_path.stem, module.run_test)
                        logging.debug(f"Registered test from module: {file_path.stem}")
                    
                    # Look for TESTS dictionary
                    if hasattr(module, "TESTS"):
                        for test_name, test_func in module.TESTS.items():
                            self.register(f"{file_path.stem}.{test_name}", test_func)
                            logging.debug(f"Registered test from module: {file_path.stem}.{test_name}")
                except Exception as e:
                    logging.error(f"Failed to load test module '{file_path.stem}': {e}")
        except Exception as e:
            logging.warning(f"Error discovering test modules: {e}")
    
    def register(self, name: str, test_func: callable):
        """
        Register a test function.
        
        Args:
            name: Test name
            test_func: Test function
        """
        self.tests[name] = test_func
    
    def get_test(self, name: str) -> Optional[callable]:
        """
        Get a test function by name.
        
        Args:
            name: Test name
            
        Returns:
            Test function or None if not found
        """
        return self.tests.get(name)
    
    def get_all_tests(self) -> Dict[str, callable]:
        """
        Get all registered tests.
        
        Returns:
            Dictionary mapping test names to test functions
        """
        return self.tests.copy()

# Create global test registry
test_registry = TestRegistry()

@app.callback()
def callback():
    """
    Run tests on File Analyzer components.
    
    The test command provides a framework for running tests on the
    File Analyzer components, including FastVLM model tests,
    JSON output validation, and more.
    """
    pass

@app.command()
def list():
    """
    List available tests.
    """
    tests = test_registry.get_all_tests()
    
    if not tests:
        console.print("[yellow]No tests registered[/yellow]")
        return
    
    # Create table of tests
    table = Table(title="Available Tests")
    table.add_column("Test Name", style="cyan")
    table.add_column("Description", style="green")
    
    for name, test_func in sorted(tests.items()):
        # Get description from function docstring
        description = test_func.__doc__
        if not description:
            description = "No description available"
        else:
            # Use first line of docstring as description
            description = description.split("\n")[0].strip()
        
        table.add_row(name, description)
    
    console.print(table)

@app.command()
def run(
    test_name: Optional[str] = typer.Argument(
        None, help="Name of the test to run (all tests if not specified)"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for test results"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", "-f", help="Stop on first test failure"
    ),
    ci: bool = typer.Option(
        False, "--ci", help="Run in CI mode (non-interactive, machine-readable output)"
    ),
    log_json: bool = typer.Option(
        False, "--log-json", help="Output logs in JSON format"
    ),
):
    """
    Run tests.
    """
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    # Configure logging
    if log_json:
        # Configure JSON logging
        import json_log_formatter
        formatter = json_log_formatter.JSONFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logging.basicConfig(level=log_level, handlers=[handler])
    else:
        # Configure regular logging
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger("file-analyzer.test")
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Run either a specific test or all tests
    if test_name:
        # Run a specific test
        test_func = test_registry.get_test(test_name)
        if not test_func:
            console.print(f"[red]Error:[/red] Test '{test_name}' not found")
            raise typer.Exit(code=1)
        
        console.print(f"Running test: [cyan]{test_name}[/cyan]")
        
        try:
            # Create test context
            context = {
                "name": test_name,
                "output_dir": output_dir,
                "verbose": verbose,
                "quiet": quiet,
                "ci": ci,
                "log_json": log_json,
                "config": config,
                "logger": logger,
                "console": console if not quiet else None,
            }
            
            # Run the test
            result = test_func(context)
            
            # Check result
            if not result or not isinstance(result, dict):
                console.print(f"[red]Error:[/red] Test '{test_name}' returned invalid result")
                raise typer.Exit(code=1)
            
            # Print result
            success = result.get("success", False)
            if success:
                console.print(f"[green]Test '{test_name}' passed[/green]")
            else:
                console.print(f"[red]Test '{test_name}' failed:[/red] {result.get('message', 'No error message')}")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]Error running test '{test_name}':[/red] {str(e)}")
            raise typer.Exit(code=1)
    else:
        # Run all tests
        tests = test_registry.get_all_tests()
        
        if not tests:
            console.print("[yellow]No tests registered[/yellow]")
            return
        
        console.print(f"Running [cyan]{len(tests)}[/cyan] tests...")
        
        # Track test results
        results = []
        
        # Run tests with progress indicator
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]Running tests...", total=len(tests))
            
            for name, test_func in sorted(tests.items()):
                progress.update(task, description=f"Running [cyan]{name}[/cyan]...")
                
                try:
                    # Create test context
                    context = {
                        "name": name,
                        "output_dir": output_dir,
                        "verbose": verbose,
                        "quiet": quiet,
                        "ci": ci,
                        "log_json": log_json,
                        "config": config,
                        "logger": logger,
                        "console": None,  # Disable console output during test
                    }
                    
                    # Run the test
                    result = test_func(context)
                    
                    # Check result
                    if not result or not isinstance(result, dict):
                        result = {
                            "name": name,
                            "success": False,
                            "message": "Invalid test result"
                        }
                    else:
                        result["name"] = name
                    
                    results.append(result)
                    
                    # Check for failure with fail_fast
                    if fail_fast and not result.get("success", False):
                        progress.update(task, completed=len(tests))
                        break
                except Exception as e:
                    results.append({
                        "name": name,
                        "success": False,
                        "message": f"Error: {str(e)}"
                    })
                    
                    # Check for failure with fail_fast
                    if fail_fast:
                        progress.update(task, completed=len(tests))
                        break
                
                progress.update(task, advance=1)
        
        # Compute summary
        passed = sum(1 for r in results if r.get("success", False))
        failed = len(results) - passed
        
        # Print summary table
        table = Table(title=f"Test Results: {passed} passed, {failed} failed")
        table.add_column("Test", style="cyan")
        table.add_column("Result", style="green")
        table.add_column("Message", style="yellow")
        
        for result in results:
            name = result.get("name", "Unknown")
            success = result.get("success", False)
            message = result.get("message", "")
            
            if success:
                result_text = "[green]PASS[/green]"
            else:
                result_text = "[red]FAIL[/red]"
            
            table.add_row(name, result_text, message)
        
        console.print(table)
        
        # Save results to output file if specified
        if output_dir:
            import json
            results_file = os.path.join(output_dir, "test_results.json")
            with open(results_file, "w") as f:
                json.dump({
                    "total": len(results),
                    "passed": passed,
                    "failed": failed,
                    "results": results
                }, f, indent=2)
            
            console.print(f"Results saved to: {results_file}")
        
        # Exit with error code if any tests failed
        if failed > 0:
            raise typer.Exit(code=1)

@app.command()
def fastvlm(
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for test results"
    ),
    model_size: str = typer.Option(
        "0.5b", "--size", "-s", help="Model size (0.5b, 1.5b, 7b)"
    ),
    use_mock: bool = typer.Option(
        False, "--mock", "-m", help="Use mock model for testing"
    ),
    test_image: Optional[str] = typer.Option(
        None, "--image", "-i", help="Path to test image (uses default if not specified)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run FastVLM model tests.
    """
    # Dynamically import the fastvlm test module
    try:
        from src.cli.test import fastvlm_tests
        
        # Create test context
        context = {
            "name": "fastvlm",
            "output_dir": output_dir,
            "verbose": verbose,
            "quiet": quiet,
            "ci": False,
            "log_json": False,
            "config": config,
            "logger": logging.getLogger("file-analyzer.test.fastvlm"),
            "console": console if not quiet else None,
            "model_size": model_size,
            "use_mock": use_mock,
            "test_image": test_image,
        }
        
        # Run the test
        result = fastvlm_tests.run_test(context)
        
        # Check result
        if not result or not isinstance(result, dict):
            console.print(f"[red]Error:[/red] FastVLM test returned invalid result")
            raise typer.Exit(code=1)
        
        # Print result
        success = result.get("success", False)
        if success:
            console.print(f"[green]FastVLM test passed[/green]")
        else:
            console.print(f"[red]FastVLM test failed:[/red] {result.get('message', 'No error message')}")
            raise typer.Exit(code=1)
    except ImportError:
        console.print("[red]Error:[/red] FastVLM test module not found")
        console.print("Please ensure that fastvlm_tests.py is present in src/cli/test directory")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error running FastVLM test:[/red] {str(e)}")
        raise typer.Exit(code=1)

@app.command()
def json(
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for test results"
    ),
    model_size: str = typer.Option(
        "0.5b", "--size", "-s", help="Model size (0.5b, 1.5b, 7b)"
    ),
    use_mock: bool = typer.Option(
        False, "--mock", "-m", help="Use mock model for testing"
    ),
    test_image: Optional[str] = typer.Option(
        None, "--image", "-i", help="Path to test image (uses default if not specified)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run JSON output validation tests.
    """
    # Dynamically import the json test module
    try:
        from src.cli.test import json_tests
        
        # Create test context
        context = {
            "name": "json",
            "output_dir": output_dir,
            "verbose": verbose,
            "quiet": quiet,
            "ci": False,
            "log_json": False,
            "config": config,
            "logger": logging.getLogger("file-analyzer.test.json"),
            "console": console if not quiet else None,
            "model_size": model_size,
            "use_mock": use_mock,
            "test_image": test_image,
        }
        
        # Run the test
        result = json_tests.run_test(context)
        
        # Check result
        if not result or not isinstance(result, dict):
            console.print(f"[red]Error:[/red] JSON test returned invalid result")
            raise typer.Exit(code=1)
        
        # Print result
        success = result.get("success", False)
        if success:
            console.print(f"[green]JSON test passed[/green]")
        else:
            console.print(f"[red]JSON test failed:[/red] {result.get('message', 'No error message')}")
            raise typer.Exit(code=1)
    except ImportError:
        console.print("[red]Error:[/red] JSON test module not found")
        console.print("Please ensure that json_tests.py is present in src/cli/test directory")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error running JSON test:[/red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()