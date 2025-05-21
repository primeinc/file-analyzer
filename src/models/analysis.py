#!/usr/bin/env python3
"""
Model Analysis CLI Tool

This tool provides command-line access to the model analysis capabilities
of the file analyzer system, with support for:

1. Single file analysis with various model types
2. Batch directory processing with parallel execution
3. Different analysis modes (describe, detect, document)
4. Output formatting options (JSON, text, markdown)
5. Custom prompts and parameters

Usage examples:
  # Analyze a single image with FastVLM
  python model_analysis.py image.jpg --model fastvlm --mode describe
  
  # Batch process a directory with FastVLM
  python model_analysis.py images/ --batch --model fastvlm --mode detect
  
  # Use a specific model size
  python model_analysis.py image.jpg --model fastvlm --size 1.5b
  
  # Custom prompt
  python model_analysis.py image.jpg --prompt "Describe this technical diagram"
  
  # Save output to specific file
  python model_analysis.py image.jpg --output results.json
  
  # Get model information
  python model_analysis.py --list-models
"""

import os
import sys
import argparse
import json
import logging
from typing import Dict, List, Any, Optional

# Fix imports by adding project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import model analyzer components
from src.model_analyzer import ModelAnalyzer
from src.model_manager import create_manager, ModelManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_output(result: Dict[str, Any], format_type: str = 'json') -> str:
    """
    Format the analysis result based on the specified format type.
    
    Args:
        result: Analysis result dictionary
        format_type: Output format type (json, text, markdown)
        
    Returns:
        Formatted output string
    """
    if format_type == 'json':
        return json.dumps(result, indent=2)
    
    elif format_type == 'text':
        # Simple text format
        output = []
        
        # Add description if present
        if 'description' in result:
            output.append("DESCRIPTION:")
            output.append(result['description'])
            output.append("")
        
        # Add tags if present
        if 'tags' in result and isinstance(result['tags'], list):
            output.append("TAGS:")
            output.append(", ".join(result['tags']))
            output.append("")
        
        # Add objects if present
        if 'objects' in result and isinstance(result['objects'], list):
            output.append("OBJECTS DETECTED:")
            for obj in result['objects']:
                if isinstance(obj, dict):
                    output.append(f"- {obj.get('name', 'Unknown')} ({obj.get('location', 'Unknown location')})")
                else:
                    output.append(f"- {obj}")
            output.append("")
        
        # Add text content if present
        if 'text' in result:
            output.append("TEXT CONTENT:")
            output.append(result['text'])
            output.append("")
        
        # Add metadata if present
        if 'metadata' in result:
            output.append("METADATA:")
            for key, value in result['metadata'].items():
                output.append(f"- {key}: {value}")
        
        return "\n".join(output)
    
    elif format_type == 'markdown':
        # Markdown format
        output = ["# Model Analysis Result", ""]
        
        # Add description if present
        if 'description' in result:
            output.append("## Description")
            output.append(result['description'])
            output.append("")
        
        # Add tags if present
        if 'tags' in result and isinstance(result['tags'], list):
            output.append("## Tags")
            tags_str = ", ".join([f"`{tag}`" for tag in result['tags']])
            output.append(tags_str)
            output.append("")
        
        # Add objects if present
        if 'objects' in result and isinstance(result['objects'], list):
            output.append("## Objects Detected")
            for obj in result['objects']:
                if isinstance(obj, dict):
                    output.append(f"- **{obj.get('name', 'Unknown')}**: {obj.get('location', 'Unknown location')}")
                else:
                    output.append(f"- {obj}")
            output.append("")
        
        # Add text content if present
        if 'text' in result:
            output.append("## Text Content")
            output.append("```")
            output.append(result['text'])
            output.append("```")
            output.append("")
        
        # Add metadata if present
        if 'metadata' in result:
            output.append("## Metadata")
            output.append("```json")
            output.append(json.dumps(result['metadata'], indent=2))
            output.append("```")
        
        return "\n".join(output)
    
    # Default to raw string representation
    return str(result)

def list_available_models(manager: ModelManager):
    """
    List all available models with their details.
    
    Args:
        manager: Model manager instance
    """
    models = manager.get_available_models()
    
    if not models:
        print("No models available")
        return
    
    print("Available models:")
    for model_name, sizes in models.items():
        size_str = ", ".join(sizes)
        print(f"  - {model_name} ({size_str})")
    
    print("\nSupported analysis modes:")
    print("  - describe: General image description with tags")
    print("  - detect: Object detection with locations")
    print("  - document: Text extraction and document type identification")

def main():
    """Main entry point for the model analysis CLI tool."""
    parser = argparse.ArgumentParser(description="Model Analysis Tool")
    
    # Allow operating with no file argument for listing models
    parser.add_argument("file", nargs='?', help="File or directory to analyze")
    
    # General options
    parser.add_argument("--model", default="fastvlm", help="Model to use")
    parser.add_argument("--size", help="Model size variant")
    parser.add_argument("--mode", default="describe", 
                       choices=["describe", "detect", "document"], 
                       help="Analysis mode")
    
    # Batch processing options
    parser.add_argument("--batch", action="store_true", 
                       help="Process directory in batch mode")
    parser.add_argument("--max-files", type=int, default=10, 
                       help="Maximum files to process in batch mode")
    parser.add_argument("--sequential", action="store_true",
                       help="Process files sequentially (batch mode only)")
    
    # Output options
    parser.add_argument("--output", help="Output file or directory")
    parser.add_argument("--format", choices=["json", "text", "markdown"], 
                       default="json", help="Output format")
    
    # Advanced options
    parser.add_argument("--prompt", help="Custom prompt for analysis")
    parser.add_argument("--model-type", choices=["vision", "text"], 
                       default="vision", help="Type of model to use")
    
    # Utility commands
    parser.add_argument("--list-models", action="store_true",
                       help="List available models and exit")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create model manager
    manager = create_manager()
    
    # List models if requested
    if args.list_models:
        list_available_models(manager)
        return 0
    
    # Ensure a file or directory is provided unless just listing models
    if not args.file:
        print("Error: No file or directory specified")
        parser.print_help()
        return 1
    
    # Check if path exists
    if not os.path.exists(args.file):
        print(f"Error: File or directory not found: {args.file}")
        return 1
    
    # Create analyzer
    analyzer = ModelAnalyzer()
    
    # Process file or directory
    try:
        if os.path.isdir(args.file) or args.batch:
            # Batch processing
            print(f"Batch processing directory: {args.file}")
            print(f"Model: {args.model} ({args.size or 'default size'})")
            print(f"Mode: {args.mode}")
            
            # Run batch analysis
            results = analyzer.batch_analyze(
                args.file,
                model_type=args.model_type,
                model_name=args.model,
                model_size=args.size,
                mode=args.mode,
                output_dir=args.output,
                max_files=args.max_files,
                prompt=args.prompt,
                parallel=not args.sequential
            )
            
            # Print summary
            summary = analyzer.get_summary()
            print(f"\nBatch processing complete:")
            print(f"- Files processed: {summary['analyses']}")
            print(f"- Successful: {summary['successful']}")
            print(f"- Failed: {summary['failed']}")
            
            # Print output location
            if args.output:
                print(f"\nResults saved to: {args.output}")
            else:
                print("\nResults saved to canonical artifact path")
        else:
            # Single file processing
            print(f"Analyzing file: {args.file}")
            print(f"Model: {args.model} ({args.size or 'default size'})")
            print(f"Mode: {args.mode}")
            
            # Run analysis
            result = analyzer.analyze_file(
                args.file,
                model_type=args.model_type,
                model_name=args.model,
                model_size=args.size,
                mode=args.mode,
                output_path=args.output,
                prompt=args.prompt
            )
            
            # Format and print result
            formatted_output = format_output(result, args.format)
            print("\nAnalysis Result:")
            print(formatted_output)
            
            # Print output location if saved
            if args.output:
                print(f"\nResult saved to: {args.output}")
            else:
                print("\nResult saved to canonical artifact path")
        
        return 0
    except Exception as e:
        print(f"Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())