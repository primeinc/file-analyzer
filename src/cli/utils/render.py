"""
Rendering utilities for file analysis output.
Handles formatting of analysis results into different output formats.
"""

import json
import re
from pathlib import Path


def render_output(analysis_data: dict, output_format: str, file_path: str) -> str:
    """
    Render analysis data into the specified output format.
    
    Args:
        analysis_data: Validated analysis data with description and tags
        output_format: Output format (pretty, json, md)
        file_path: Original file path for context
        
    Returns:
        Formatted output string
    """
    file_path_obj = Path(file_path)
    file_ext = file_path_obj.suffix
    
    # Generate recommended filename from description
    description = analysis_data.get('description', '')
    clean_desc = re.sub(r'[^\w\s-]', '', description[:50]).strip()
    clean_desc = re.sub(r'[-\s]+', '-', clean_desc).lower()
    recommended_filename = f"{clean_desc}{file_ext}"
    
    if output_format == "json":
        output_data = {
            "recommended_filename": recommended_filename,
            "description": analysis_data.get('description', ''),
            "tags": analysis_data.get('tags', []),
            "metadata": analysis_data.get('metadata', {}),
            "original_file": file_path
        }
        return json.dumps(output_data, indent=2)
    
    elif output_format == "md":
        tags_str = ", ".join(analysis_data.get('tags', []))
        return f"""# File Analysis: {file_path_obj.name}

**Recommended Filename:** `{recommended_filename}`

## Description
{analysis_data.get('description', 'No description available')}

## Tags
{tags_str}

## Metadata
- Model: {analysis_data.get('metadata', {}).get('model', 'fastvlm_1.5b')}
- Execution Time: {analysis_data.get('metadata', {}).get('execution_time', 'N/A')} seconds
"""
    
    else:  # pretty format (default)
        tags_str = ", ".join(analysis_data.get('tags', []))
        return f"""Recommended Filename: {recommended_filename}

Description:
{analysis_data.get('description', 'No description available')}

Tags: {tags_str}

Analysis Time: {analysis_data.get('metadata', {}).get('execution_time', 'N/A')} seconds
"""