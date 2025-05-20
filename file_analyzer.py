#!/usr/bin/env python3
"""
Unified File Analysis System

Combines multiple tools for comprehensive file analysis:
- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract: OCR for images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis
"""

import os
import sys
import subprocess
import argparse
import json
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Required external tools and their corresponding analysis types
REQUIRED_TOOLS = {
    "exiftool": "metadata",
    "rdfind": "duplicates",
    "tesseract": "ocr",
    "clamscan": "malware",
    "rg": "search",
    "binwalk": "binary"
}

def check_dependencies(required_tools=None):
    """Check if required external tools are installed and available in PATH."""
    if required_tools is None:
        required_tools = REQUIRED_TOOLS
    
    missing_tools = {}
    
    for tool, analysis_type in required_tools.items():
        if shutil.which(tool) is None:
            missing_tools[tool] = analysis_type
    
    return missing_tools


class FileAnalyzer:
    def __init__(self, path, output_dir=None):
        self.path = Path(path).expanduser().absolute()
        if not self.path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.path}")
        
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "path": str(self.path),
            "time": datetime.now().isoformat(),
            "analyses": {}
        }
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
        
    def run_command(self, command, shell=False):
        try:
            result = subprocess.run(command, shell=shell, check=True, 
                                  capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr}")
            return None

    def extract_metadata(self):
        print(f"Extracting metadata from {self.path}...")
        
        command = ["exiftool", "-json", "-r" if self.path.is_dir() else "", str(self.path)]
        command = [c for c in command if c]  # Remove empty elements
        
        output = self.run_command(command)
        if not output:
            self.results["analyses"]["metadata"] = {"status": "error"}
            return None
            
        try:
            metadata = json.loads(output)
            output_file = self.output_dir / f"metadata_{self.timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"Metadata saved to {output_file}")
            self.results["analyses"]["metadata"] = {
                "status": "success",
                "file": str(output_file),
                "count": len(metadata)
            }
            return metadata
        except json.JSONDecodeError:
            self.results["analyses"]["metadata"] = {"status": "error"}
            return None

    def find_duplicates(self):
        print(f"Finding duplicates in {self.path}...")
        
        if self.path.is_file():
            print("Duplicate finding only works on directories.")
            self.results["analyses"]["duplicates"] = {"status": "skipped"}
            return None
        
        results_file = self.output_dir / f"duplicates_{self.timestamp}.txt"
        command = ["rdfind", "-outputname", str(results_file), str(self.path)]
        output = self.run_command(command)
        
        if output and results_file.exists():
            print(f"Duplicate analysis saved to {results_file}")
            self.results["analyses"]["duplicates"] = {
                "status": "success",
                "file": str(results_file)
            }
            return results_file
        else:
            self.results["analyses"]["duplicates"] = {"status": "error"}
            return None

    def perform_ocr(self):
        print(f"Performing OCR on images in {self.path}...")
        
        # Find image files
        image_files = []
        if self.path.is_dir():
            for root, _, files in os.walk(self.path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in self.image_extensions:
                        image_files.append(file_path)
        elif self.path.suffix.lower() in self.image_extensions:
            image_files.append(self.path)
        
        if not image_files:
            print("No supported image files found.")
            self.results["analyses"]["ocr"] = {"status": "skipped"}
            return None
        
        # Process images (limit to 50 for performance)
        ocr_results = {}
        
        def process_image(img_path):
            try:
                output = self.run_command(["tesseract", str(img_path), "stdout"])
                return str(img_path), output.strip() if output else "No text extracted"
            except Exception as e:
                return str(img_path), f"Error: {str(e)}"
        
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            for img_path, text in executor.map(process_image, image_files[:50]):
                ocr_results[img_path] = text
        
        # Save results
        output_file = self.output_dir / f"ocr_results_{self.timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(ocr_results, f, indent=2)
        
        print(f"OCR results saved to {output_file}")
        self.results["analyses"]["ocr"] = {
            "status": "success",
            "file": str(output_file),
            "count": len(ocr_results)
        }
        
        return ocr_results

    def scan_malware(self):
        print(f"Scanning for malware in {self.path}...")
        
        command = ["clamscan", "-r", "--bell", "-i", str(self.path)]
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"malware_scan_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            print(f"Malware scan results saved to {output_file}")
            self.results["analyses"]["malware"] = {
                "status": "success",
                "file": str(output_file)
            }
            return output
        else:
            self.results["analyses"]["malware"] = {"status": "error"}
            return None

    def search_content(self, search_text):
        print(f"Searching for '{search_text}' in {self.path}...")
        
        if not search_text:
            self.results["analyses"]["search"] = {"status": "skipped"}
            return None
        
        command = ["rg", "-i", "--line-number", search_text, str(self.path)]
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"search_{search_text}_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            match_count = len(output.splitlines())
            print(f"Found {match_count} matches. Results saved to {output_file}")
            self.results["analyses"]["search"] = {
                "status": "success", 
                "query": search_text,
                "file": str(output_file),
                "matches": match_count
            }
            return output
        else:
            self.results["analyses"]["search"] = {
                "status": "completed",
                "query": search_text,
                "matches": 0
            }
            return None

    def analyze_binary(self):
        print(f"Analyzing binary content in {self.path}...")
        
        if self.path.is_dir():
            print("Binary analysis needs a specific file.")
            self.results["analyses"]["binary"] = {"status": "skipped"}
            return None
        
        command = ["binwalk", "-B", "-e", "--term", str(self.path)]
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"binary_analysis_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            print(f"Binary analysis saved to {output_file}")
            self.results["analyses"]["binary"] = {
                "status": "success",
                "file": str(output_file)
            }
            return output
        else:
            self.results["analyses"]["binary"] = {"status": "error"}
            return None

    def save_results(self):
        results_file = self.output_dir / f"analysis_summary_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nAnalysis complete. Summary saved to {results_file}")
        return results_file


def main():
    parser = argparse.ArgumentParser(description='File Analysis System')
    parser.add_argument('path', help='Path to file/directory to analyze')
    parser.add_argument('--metadata', '-m', action='store_true', help='Extract metadata')
    parser.add_argument('--duplicates', '-d', action='store_true', help='Find duplicates')
    parser.add_argument('--ocr', '-o', action='store_true', help='Perform OCR')
    parser.add_argument('--malware', '-v', action='store_true', help='Scan for malware')
    parser.add_argument('--search', '-s', help='Search content')
    parser.add_argument('--binary', '-b', action='store_true', help='Analyze binary')
    parser.add_argument('--all', '-a', action='store_true', help='All analyses')
    parser.add_argument('--output', '-r', help='Output directory')
    parser.add_argument('--skip-dependency-check', action='store_true', 
                        help='Skip checking for required external tools')
    
    args = parser.parse_args()
    
    try:
        # Determine which analyses to run
        run_all = args.all or not any([
            args.metadata, args.duplicates, args.ocr, 
            args.malware, args.search, args.binary
        ])
        
        # Check for required tools based on requested analyses
        if not args.skip_dependency_check:
            tools_to_check = {}
            if run_all or args.metadata:
                tools_to_check["exiftool"] = "metadata"
            if run_all or args.duplicates:
                tools_to_check["rdfind"] = "duplicates"
            if run_all or args.ocr:
                tools_to_check["tesseract"] = "ocr"
            if run_all or args.malware:
                tools_to_check["clamscan"] = "malware"
            if args.search:
                tools_to_check["rg"] = "search"
            if (run_all or args.binary):
                tools_to_check["binwalk"] = "binary"
            
            missing_tools = check_dependencies(tools_to_check)
            
            if missing_tools:
                print("ERROR: Missing required tools for requested analyses:")
                for tool, analysis in missing_tools.items():
                    print(f"  - {tool}: required for {analysis} analysis")
                print("\nPlease install the missing tools and try again.")
                print("Installation instructions can be found in the project documentation.")
                sys.exit(1)
        
        analyzer = FileAnalyzer(args.path, args.output)
        
        if run_all or args.metadata:
            analyzer.extract_metadata()
        
        if run_all or args.duplicates:
            analyzer.find_duplicates()
        
        if run_all or args.ocr:
            analyzer.perform_ocr()
        
        if run_all or args.malware:
            analyzer.scan_malware()
        
        if args.search:
            analyzer.search_content(args.search)
        
        if (run_all or args.binary) and not args.path.is_dir():
            analyzer.analyze_binary()
        
        analyzer.save_results()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()