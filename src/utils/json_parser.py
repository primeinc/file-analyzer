#!/usr/bin/env python3
"""
Simple JSON parser utility for bash scripts

This script provides a simple command-line tool for extracting values from JSON files,
designed to be easily called from bash scripts without requiring additional dependencies.

Usage:
    python3 json_parser.py <file_path> <key> [default_value]

Where:
    file_path: Path to the JSON file
    key: Key to extract (can be nested with dot notation, e.g., 'context.description')
    default_value: Optional default value if the key is not found

Example:
    python3 json_parser.py manifest.json retention_days 7
    python3 json_parser.py config.json structure.test ""
"""

import json
import sys
from typing import Any, Optional


def get_json_value(file_path: str, key: str, default: Optional[Any] = None) -> Any:
    """
    Extract a value from a JSON file by key.
    
    Args:
        file_path: Path to the JSON file
        key: Key to extract (can be nested with dot notation, e.g., 'context.description')
        default: Default value if the key is not found
        
    Returns:
        The value as a string, or the default value if not found
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Handle nested keys with dot notation
        if '.' in key:
            keys = key.split('.')
            value = data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        else:
            return data.get(key, default)
    except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
        # Return default on any error
        return default


def main():
    """Command-line interface"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <file_path> <key> [default_value]", file=sys.stderr)
        sys.exit(1)
        
    file_path = sys.argv[1]
    key = sys.argv[2]
    default = sys.argv[3] if len(sys.argv) > 3 else None
    
    value = get_json_value(file_path, key, default)
    
    # Always print as string for shell script consumption
    if value is not None:
        print(value)
    elif default is not None:
        print(default)


if __name__ == "__main__":
    main()