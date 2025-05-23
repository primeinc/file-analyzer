"""
Rendering utilities for file analysis output.
Handles formatting of analysis results into different output formats.
"""

import json
import re
import logging
from pathlib import Path
from collections import Counter


def clean_tags(tags: list) -> list:
    """
    Clean and deduplicate tags, keeping only the most relevant ones.
    
    Args:
        tags: Raw list of tags from model
        
    Returns:
        Cleaned and deduplicated list of tags (max 10)
    """
    if not tags:
        return []
    
    # Convert to lowercase and count occurrences
    tag_counts = Counter(tag.lower().strip() for tag in tags if tag.strip())
    
    # Remove generic/bad tags
    generic_tags = {'image', 'picture', 'photo', 'shooting', 'sh', 'shock', 'shockingly'}
    filtered_counts = {tag: count for tag, count in tag_counts.items() 
                      if tag not in generic_tags and len(tag) > 2}
    
    # Sort by frequency (most common first), then alphabetically
    sorted_tags = sorted(filtered_counts.items(), key=lambda x: (-x[1], x[0]))
    
    # Return top 10 unique tags
    return [tag for tag, _ in sorted_tags[:10]]


def generate_intelligent_filename(description: str, image_path: str, file_ext: str) -> str:
    """
    Generate an intelligent filename using the FastVLM adapter.
    
    Args:
        description: The image description from the initial analysis
        image_path: Path to the actual image file for re-analysis
        file_ext: The original file extension
        
    Returns:
        Recommended filename with extension
    """
    logger = logging.getLogger(__name__)
    
    try:
        from src.models.fastvlm.adapter import create_adapter
        
        # Use a targeted prompt for filename generation
        filename_prompt = """Look at this image and suggest a short, descriptive filename.

Rules:
- 2-4 words maximum
- Focus on the main subject/object
- Use hyphens between words
- No generic words like "image", "picture", "simple"
- Be specific and concrete

Examples:
- "red-car-sunset" 
- "cat-sleeping-chair"
- "letter-t-icon"
- "pizza-slice-table"

Respond with ONLY the filename (no extension), nothing else."""
        
        # Create adapter and use proper predict method
        adapter = create_adapter("fastvlm", "1.5b", auto_download=False)
        
        # Use the adapter's predict method which includes all the robust error handling,
        # JSON repair, timeout handling, and output processing
        result = adapter.predict(
            image_path=image_path,
            prompt=filename_prompt,
            mode="describe",
            max_new_tokens=50  # Short response for filename
        )
        
        # Extract the suggested filename from the adapter result
        if isinstance(result, dict):
            # Try to get from description field first
            suggested_name = result.get("description", "").strip()
            # If empty, try other fields that might contain the response
            if not suggested_name:
                suggested_name = result.get("text", result.get("response", "")).strip()
        else:
            suggested_name = str(result).strip()
            
        # Clean up the suggestion
        suggested_name = re.sub(r'[^\w\s-]', '', suggested_name.lower())
        suggested_name = re.sub(r'\s+', '-', suggested_name)
        suggested_name = re.sub(r'-+', '-', suggested_name)
        suggested_name = suggested_name.strip('-')
        
        # Validate the suggestion
        if suggested_name and 3 <= len(suggested_name) <= 50:
            logger.debug(f"Model suggested filename: {suggested_name}")
            return f"{suggested_name}{file_ext}"
            
    except Exception as e:
        logger.debug(f"Model filename generation failed: {e}")
    
    # Fallback: Extract nouns/objects from description
    return _extract_filename_from_description(description, file_ext)


def _extract_filename_from_description(description: str, file_ext: str) -> str:
    """Fallback: Extract concrete nouns from description."""
    
    # Look for specific content mentions
    content_patterns = [
        r'\bletter\s+[\'"]?([A-Z])[\'"]?',  # "letter T" -> "letter-t"
        r'\bnumber\s+[\'"]?(\d+)[\'"]?',    # "number 5" -> "number-5"
        r'\bicon\s+of\s+a?\s*(\w+)',       # "icon of a star" -> "icon-star"
        r'\bsymbol\s+([A-Z])\b',           # "symbol T" -> "symbol-t"
    ]
    
    for pattern in content_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            content = match.group(1).lower()
            # Extract the type from the pattern
            if 'letter' in pattern:
                prefix = 'letter'
            elif 'number' in pattern:
                prefix = 'number'
            elif 'icon' in pattern:
                prefix = 'icon'
            elif 'symbol' in pattern:
                prefix = 'symbol'
            else:
                prefix = 'item'
            return f"{prefix}-{content}{file_ext}"
    
    # Look for key nouns/objects mentioned
    key_objects = re.findall(r'\b(?:duck|penguin|cat|dog|car|house|tree|book|phone|icon|symbol|letter|number|logo|sign)\b', 
                            description.lower())
    
    if key_objects:
        # Use the first 1-2 key objects
        filename = '-'.join(key_objects[:2])
        return f"{filename}{file_ext}"
    
    # Extract any capitalized words (proper nouns) 
    proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', description)
    if proper_nouns:
        # Filter out common words like "The", "Of", "In"
        significant_nouns = [noun for noun in proper_nouns 
                           if noun.lower() not in ['the', 'of', 'in', 'at', 'on', 'a', 'an']]
        if significant_nouns:
            filename = '-'.join(significant_nouns[:3]).lower()  # Take up to 3 words
            filename = re.sub(r'[^\w-]', '', filename)
            if len(filename) > 3:
                return f"{filename}{file_ext}"
    
    # Final fallback
    return f"unknown-content{file_ext}"


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
    
    # Generate intelligent filename recommendation
    description = analysis_data.get('description', '')
    recommended_filename = generate_intelligent_filename(description, file_path, file_ext)
    
    # Clean and deduplicate tags
    raw_tags = analysis_data.get('tags', [])
    clean_tag_list = clean_tags(raw_tags)
    
    if output_format == "json":
        output_data = {
            "recommended_filename": recommended_filename,
            "description": description,
            "tags": clean_tag_list,
            "metadata": analysis_data.get('metadata', {}),
            "original_file": file_path
        }
        return json.dumps(output_data, indent=2)
    
    elif output_format == "md":
        tags_str = ", ".join(clean_tag_list)
        return f"""# File Analysis: {file_path_obj.name}

**Recommended Filename:** `{recommended_filename}`

## Description
{description}

## Tags
{tags_str}

## Metadata
- Model: {analysis_data.get('metadata', {}).get('model', 'fastvlm_1.5b')}
- Execution Time: {analysis_data.get('metadata', {}).get('execution_time', 'N/A')} seconds
"""
    
    else:  # pretty format (default)
        tags_str = ", ".join(clean_tag_list)
        return f"""Recommended Filename: {recommended_filename}

Description:
{description}

Tags: {tags_str}

Analysis Time: {analysis_data.get('metadata', {}).get('execution_time', 'N/A')} seconds
"""