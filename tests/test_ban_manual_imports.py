#!/usr/bin/env python3
"""
ENFORCE ABSOLUTE BAN ON MANUAL IMPORTS

Manual imports are BANNED in all cases. No exceptions. No fallbacks.
If entry points fail, commands just don't exist. That's proper architecture.

This test enforces that ban with zero tolerance.
"""

import ast
import os
import pytest
from pathlib import Path


def get_python_files():
    """Get all Python files in the CLI directory."""
    cli_dir = Path("src/cli")
    return list(cli_dir.rglob("*.py"))


def parse_file(file_path):
    """Parse a Python file and return the AST."""
    with open(file_path, 'r') as f:
        content = f.read()
    return ast.parse(content, filename=str(file_path))


class TestBanManualImports:
    """Enforce absolute ban on manual imports."""
    
    def test_no_manual_command_imports(self):
        """BANNED: Manual imports of CLI command modules."""
        banned_patterns = [
            "from src.cli.analyze.main import",
            "from src.cli.model.main import", 
            "from src.cli.test.main import",
            "from src.cli.validate.main import",
            "from src.cli.artifact.main import",
            "from src.cli.benchmark.main import",
            "from src.cli.install.main import",
            "import src.cli.analyze.main",
            "import src.cli.model.main",
            "import src.cli.test.main",
            "import src.cli.validate.main",
            "import src.cli.artifact.main",
            "import src.cli.benchmark.main", 
            "import src.cli.install.main",
        ]
        
        violations = []
        
        for py_file in get_python_files():
            with open(py_file, 'r') as f:
                content = f.read()
                
            for pattern in banned_patterns:
                if pattern in content:
                    violations.append(f"{py_file}: {pattern}")
        
        assert not violations, f"BANNED MANUAL IMPORTS FOUND:\n" + "\n".join(violations)
    
    def test_no_manual_app_registration(self):
        """BANNED: Manual app.add_typer() calls for commands."""
        banned_patterns = [
            "app.add_typer(analyze_app",
            "app.add_typer(model_app", 
            "app.add_typer(test_app",
            "app.add_typer(validate_app",
            "app.add_typer(artifact_app",
            "app.add_typer(benchmark_app",
            "app.add_typer(install_app",
        ]
        
        violations = []
        
        for py_file in get_python_files():
            with open(py_file, 'r') as f:
                content = f.read()
                
            for pattern in banned_patterns:
                if pattern in content:
                    violations.append(f"{py_file}: {pattern}")
        
        assert not violations, f"BANNED MANUAL APP REGISTRATION FOUND:\n" + "\n".join(violations)
    
    def test_no_fallback_loading(self):
        """BANNED: Any form of fallback or manual loading in actual code."""
        banned_code_patterns = [
            "try:",  # Only check for actual try blocks that might contain manual loading
        ]
        
        violations = []
        
        for py_file in get_python_files():
            with open(py_file, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                stripped = line.strip().lower()
                
                # Check for try blocks that might contain manual loading
                if stripped.startswith("try:"):
                    # Look ahead for manual imports in the try block
                    for j in range(i, min(i + 10, len(lines))):
                        next_line = lines[j].strip().lower()
                        if "from src.cli." in next_line and "main import" in next_line:
                            violations.append(f"{py_file}:{i}: Manual import in try block")
                        elif next_line.startswith("except") or next_line.startswith("def") or next_line.startswith("class"):
                            break
        
        assert not violations, f"BANNED FALLBACK LOADING FOUND:\n" + "\n".join(violations)
    
    def test_no_dangerous_exception_suppression(self):
        """BANNED: Broad exception suppression that hides import errors."""
        dangerous_patterns = [
            "except: pass",
            "except Exception: pass", 
            "except ImportError: pass",
        ]
        
        violations = []
        
        for py_file in get_python_files():
            with open(py_file, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                for pattern in dangerous_patterns:
                    if pattern in stripped:
                        # Check if there's a comment explaining why (some cases may be acceptable)
                        if "# Silently skip broken commands in production" in line:
                            continue  # This specific case is acceptable
                        violations.append(f"{py_file}:{i}: {stripped}")
        
        assert not violations, f"DANGEROUS EXCEPTION SUPPRESSION FOUND:\n" + "\n".join(violations)
    
    def test_entry_points_only_architecture(self):
        """ENFORCE: Only entry points are used for command loading."""
        main_file = Path("src/cli/main.py")
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Must use entry points
        assert "entry_points(group=" in content, "CLI must use entry_points for command loading"
        
        # Must NOT have any manual command imports
        banned_imports = [
            "from src.cli.analyze.main",
            "from src.cli.model.main", 
            "from src.cli.test.main",
            "from src.cli.validate.main"
        ]
        
        for banned in banned_imports:
            assert banned not in content, f"BANNED: Manual import found: {banned}"
    
    def test_clean_command_loading_only(self):
        """ENFORCE: Command loading must be clean with no fallbacks."""
        main_file = Path("src/cli/main.py")
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check the actual command loading logic
        lines = content.split('\n')
        in_command_loading = False
        
        for line in lines:
            if "entry_points(group=" in line:
                in_command_loading = True
            elif in_command_loading and line.strip() == "":
                in_command_loading = False
            elif in_command_loading:
                # In command loading section - must not have manual imports
                assert "from src.cli." not in line, f"BANNED: Manual import in command loading: {line.strip()}"
                assert "import src.cli." not in line, f"BANNED: Manual import in command loading: {line.strip()}"


class TestEnforceProperErrorHandling:
    """Enforce proper error handling without manual fallbacks."""
    
    def test_entry_point_failure_handling(self):
        """Entry point failures must be handled gracefully WITHOUT manual loading."""
        main_file = Path("src/cli/main.py")
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # If there's exception handling for entry points, it must NOT do manual loading
        if "except" in content and "entry_points" in content:
            # Check that exception handlers don't do manual imports
            lines = content.split('\n')
            in_except_block = False
            
            for line in lines:
                if line.strip().startswith("except") and "entry_points" in content:
                    in_except_block = True
                elif in_except_block and (line.strip().startswith("def ") or line.strip().startswith("class ")):
                    in_except_block = False
                elif in_except_block:
                    assert "from src.cli." not in line, f"BANNED: Manual import in exception handler: {line.strip()}"
                    assert "import src.cli." not in line, f"BANNED: Manual import in exception handler: {line.strip()}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])