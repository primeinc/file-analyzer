#!/usr/bin/env python3
"""
Main file analyzer entry point

Provides a unified interface for all file analysis capabilities:
- Metadata extraction
- Duplicate detection
- OCR text extraction
- Malware scanning
- Content searching
- Binary analysis
- AI-powered model analysis

This replaces the previous file_analyzer.py with a more maintainable
Python-only implementation instead of relying on the bash script.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import artifact discipline components
from src.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    safe_write
)

# Import model analysis components
from src.model_analyzer import ModelAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileAnalyzer:
    """Main class for the file analyzer system."""
    
    def __init__(self, config=None):
        """Initialize the file analyzer with optional configuration."""
        self.config = config or {}
        self.results = {}
        self.model_analyzer = ModelAnalyzer(self.config)
        
    def analyze(self, path, options):
        """Main analysis method that coordinates all analysis types."""
        logging.info(f"Analyzing {path} with options: {options}")
        
        # Create canonical artifact path for this analysis run
        artifact_dir = get_canonical_artifact_path("analysis", "file_analysis")
        logging.info(f"Using artifact directory: {artifact_dir}")
        
        # Use PathGuard to enforce artifact discipline
        with PathGuard(artifact_dir):
            # Individual analysis components
            if options.get('metadata'):
                self._extract_metadata(path, artifact_dir)
                
            if options.get('duplicates'):
                self._find_duplicates(path, artifact_dir)
                
            if options.get('ocr'):
                self._perform_ocr(path, artifact_dir)
                
            if options.get('virus'):
                self._scan_malware(path, artifact_dir)
                
            if options.get('search'):
                self._search_content(path, options.get('search_text', ''), artifact_dir)
                
            if options.get('binary'):
                self._analyze_binary(path, artifact_dir)
                
            if options.get('vision') or options.get('model'):
                self._analyze_models(
                    path, 
                    options.get('model_type', 'vision'),
                    options.get('model_name', 'fastvlm'), 
                    options.get('model_mode', 'describe'),
                    artifact_dir
                )
            
            # Write summary of all analyses
            self._write_summary(artifact_dir)
            
        return self.results
    
    def _extract_metadata(self, path, artifact_dir):
        """Extract metadata from files."""
        logging.info(f"Extracting metadata from {path}")
        
        # Implementation to be added
        self.results['metadata'] = {
            'status': 'skipped',
            'message': 'Metadata extraction not implemented yet'
        }
        
    def _find_duplicates(self, path, artifact_dir):
        """Find duplicate files."""
        logging.info(f"Finding duplicates in {path}")
        
        # Implementation to be added
        self.results['duplicates'] = {
            'status': 'skipped',
            'message': 'Duplicate detection not implemented yet'
        }
        
    def _perform_ocr(self, path, artifact_dir):
        """Perform OCR on images."""
        logging.info(f"Performing OCR on images in {path}")
        
        # Implementation to be added
        self.results['ocr'] = {
            'status': 'skipped',
            'message': 'OCR not implemented yet'
        }
        
    def _scan_malware(self, path, artifact_dir):
        """Scan for malware."""
        logging.info(f"Scanning for malware in {path}")
        
        # Implementation to be added
        self.results['virus'] = {
            'status': 'skipped',
            'message': 'Malware scanning not implemented yet'
        }
        
    def _search_content(self, path, search_text, artifact_dir):
        """Search content for specific text."""
        logging.info(f"Searching for '{search_text}' in {path}")
        
        # Implementation to be added
        self.results['search'] = {
            'status': 'skipped',
            'message': 'Content searching not implemented yet'
        }
        
    def _analyze_binary(self, path, artifact_dir):
        """Analyze binary files."""
        logging.info(f"Analyzing binary files in {path}")
        
        # Implementation to be added
        self.results['binary'] = {
            'status': 'skipped',
            'message': 'Binary analysis not implemented yet'
        }
        
    def _analyze_models(self, path, model_type, model_name, model_mode, artifact_dir):
        """
        Analyze files with AI models using the ModelAnalyzer.
        
        Args:
            path: Path to file or directory to analyze
            model_type: Type of model to use (vision, text, etc.)
            model_name: Name of model to use (fastvlm, etc.)
            model_mode: Analysis mode (describe, detect, document, etc.)
            artifact_dir: Directory for output artifacts
        """
        logging.info(f"Analyzing with {model_name} model in {model_mode} mode")
        
        # Determine if this is a single file or directory
        is_directory = os.path.isdir(path)
        
        # Output path within artifact directory
        output_path = None
        if is_directory:
            output_path = os.path.join(artifact_dir, f"{model_type}_{model_name}_{model_mode}")
            os.makedirs(output_path, exist_ok=True)
        else:
            file_base = os.path.splitext(os.path.basename(path))[0]
            output_path = os.path.join(artifact_dir, f"{file_base}_{model_name}_{model_mode}.json")
        
        # Get model size from config if available
        model_size = self.config.get('vision', {}).get('model_size', None)
        
        try:
            # Run analysis
            if is_directory:
                # Batch processing for directories
                batch_results = self.model_analyzer.batch_analyze(
                    path, 
                    model_type=model_type,
                    model_name=model_name,
                    model_size=model_size,
                    mode=model_mode,
                    output_dir=output_path
                )
                
                # Store summary in results
                summary = self.model_analyzer.get_summary()
                self.results[model_type] = {
                    'status': 'success',
                    'model': model_name,
                    'mode': model_mode,
                    'files_processed': len(batch_results),
                    'successful': summary['successful'],
                    'failed': summary['failed'],
                    'output_dir': output_path
                }
            else:
                # Single file processing
                result = self.model_analyzer.analyze_file(
                    path, 
                    model_type=model_type,
                    model_name=model_name,
                    model_size=model_size,
                    mode=model_mode,
                    output_path=output_path
                )
                
                # Store result in results
                self.results[model_type] = {
                    'status': 'success' if 'error' not in result else 'error',
                    'model': model_name,
                    'mode': model_mode,
                    'output_path': output_path
                }
        except Exception as e:
            logging.error(f"Error in model analysis: {e}")
            self.results[model_type] = {
                'status': 'error',
                'model': model_name,
                'mode': model_mode,
                'error': str(e)
            }
        
    def _write_summary(self, artifact_dir):
        """Write a summary of all analyses."""
        summary_file = os.path.join(artifact_dir, "analysis_summary.json")
        safe_write(summary_file, json.dumps(self.results, indent=2))
        logging.info(f"Summary written to {summary_file}")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="File Analysis System")
    
    # Required arguments
    parser.add_argument("path", help="Path to analyze (file or directory)")
    
    # Analysis options
    parser.add_argument("-a", "--all", action="store_true", help="Run all analyses")
    parser.add_argument("-m", "--metadata", action="store_true", help="Extract metadata")
    parser.add_argument("-d", "--duplicates", action="store_true", help="Find duplicates")
    parser.add_argument("-o", "--ocr", action="store_true", help="Perform OCR on images")
    parser.add_argument("-v", "--virus", action="store_true", help="Scan for malware")
    parser.add_argument("-s", "--search", metavar="TEXT", help="Search content")
    parser.add_argument("-b", "--binary", action="store_true", help="Analyze binary files")
    parser.add_argument("-V", "--vision", action="store_true", help="Analyze images with AI vision models")
    
    # Model analysis options
    parser.add_argument("--model", help="Specify model to use for analysis")
    parser.add_argument("--model-type", choices=["vision", "text"], default="vision", 
                      help="Type of model to use")
    parser.add_argument("--model-size", help="Size/variant of the model to use")
    
    # Output options
    parser.add_argument("-r", "--results", metavar="DIR", help="Output directory")
    
    # Vision options
    parser.add_argument("--vision-model", choices=["fastvlm", "bakllava", "qwen2vl"], 
                      default="fastvlm", help="Vision model to use")
    parser.add_argument("--vision-mode", choices=["describe", "detect", "document"], 
                      default="describe", help="Vision analysis mode")
    
    return parser.parse_args()

def main():
    """Entry point for the file analyzer."""
    args = parse_args()
    
    # Create options dictionary from arguments
    options = {
        'metadata': args.metadata or args.all,
        'duplicates': args.duplicates or args.all,
        'ocr': args.ocr or args.all,
        'virus': args.virus or args.all,
        'search': args.search is not None or args.all,
        'search_text': args.search or '',
        'binary': args.binary or args.all,
        'vision': args.vision or args.all,
        'model': args.model is not None,
        'model_type': args.model_type,
        'model_name': args.model or args.vision_model,
        'model_mode': args.vision_mode,
        'results_dir': args.results
    }
    
    # Create configuration dictionary
    config = {
        'vision': {
            'model': args.vision_model,
            'model_size': args.model_size,
            'mode': args.vision_mode
        }
    }
    
    # Initialize and run the analyzer
    analyzer = FileAnalyzer(config)
    results = analyzer.analyze(args.path, options)
    
    # Return success
    return 0

if __name__ == "__main__":
    sys.exit(main())