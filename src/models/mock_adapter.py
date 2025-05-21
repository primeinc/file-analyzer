#!/usr/bin/env python3
"""
Mock Model Adapter - Example implementation for testing

This module provides a mock model adapter implementation that can be used
for testing the model analysis system without requiring actual model files
or dependencies. It returns predefined responses based on input parameters.

Features:
1. Simulates different model types and sizes
2. Supports all standard analysis modes
3. Generates realistic-looking responses with proper JSON structure
4. Includes proper metadata and timing information
5. Can be used as a reference implementation for new adapters
"""

import os
import sys
import json
import logging
import random
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockModelAdapter:
    """Mock model adapter for testing purposes."""
    
    def __init__(self, model_type: str = "mock", model_size: str = "small", **kwargs):
        """
        Initialize the mock model adapter.
        
        Args:
            model_type: Type of model to simulate
            model_size: Size of model to simulate
            **kwargs: Additional parameters
        """
        self.model_type = model_type
        self.model_size = model_size
        self.config = kwargs
        logger.info(f"Initialized {model_type} mock model adapter ({model_size})")
    
    def predict(self, input_path: str, prompt: Optional[str] = None, 
               output_path: Optional[str] = None, mode: str = "describe",
               **kwargs) -> Dict[str, Any]:
        """
        Run prediction with the mock model.
        
        Args:
            input_path: Path to input file
            prompt: Optional prompt to guide generation
            output_path: Optional path to save output
            mode: Analysis mode (describe, detect, document)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with prediction results
        """
        logger.info(f"Running mock prediction on {input_path} in {mode} mode")
        
        # Simulate processing time
        start_time = time.time()
        time.sleep(0.5)  # Simulate work being done
        
        # Extract file basename for personalized response
        file_name = os.path.basename(input_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Generate appropriate response based on mode
        if mode == "describe":
            result = self._generate_description(file_name, file_ext, prompt)
        elif mode == "detect":
            result = self._generate_detection(file_name, file_ext, prompt)
        elif mode == "document":
            result = self._generate_document(file_name, file_ext, prompt)
        else:
            # Default to description
            result = self._generate_description(file_name, file_ext, prompt)
        
        # Add standard metadata
        execution_time = time.time() - start_time
        result["metadata"] = {
            "model": f"{self.model_type}_{self.model_size}",
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "mock": True
        }
        
        # Add prompt if provided
        if prompt:
            result["metadata"]["prompt"] = prompt
        
        # Save result if output path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved result to {output_path}")
        
        return result
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this model adapter.
        
        Returns:
            Dictionary with model information
        """
        return {
            "name": "MockModelAdapter",
            "type": self.model_type,
            "size": self.model_size,
            "description": "Mock model adapter for testing purposes",
            "capabilities": ["describe", "detect", "document"],
            "mock": True
        }
    
    def _generate_description(self, file_name: str, file_ext: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a mock image description.
        
        Args:
            file_name: Name of the input file
            file_ext: File extension
            prompt: Optional prompt to guide generation
            
        Returns:
            Dictionary with description and tags
        """
        # Determine if this is an image file
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]
        is_image = file_ext in image_exts
        
        if is_image:
            # Generate image description
            descriptions = [
                f"This image shows a {random.choice(['landscape', 'portrait', 'still life', 'abstract composition'])} with {random.choice(['vibrant', 'muted', 'contrast-heavy', 'pastel'])} colors.",
                f"The photograph {file_name} captures a {random.choice(['natural', 'urban', 'indoor', 'outdoor'])} scene with {random.choice(['people', 'animals', 'buildings', 'natural elements'])}.",
                f"A {random.choice(['detailed', 'minimalist', 'high-contrast', 'colorful'])} image depicting {random.choice(['everyday life', 'nature', 'technology', 'art'])}."
            ]
            
            # Generate appropriate tags
            tag_sets = [
                ["photo", "image", file_ext[1:], random.choice(["color", "blackandwhite"])],
                ["visual", "picture", "photography", random.choice(["highresolution", "lowresolution"])],
                ["snapshot", "digital", random.choice(["landscape", "portrait"]), "media"]
            ]
            
            # Choose a random description and tags
            description = random.choice(descriptions)
            tags = random.choice(tag_sets)
            
            # Add filename-specific tag
            tags.append(file_name.split(".")[0].lower())
            
        else:
            # Non-image file
            description = f"This appears to be a {file_ext[1:]} file named '{file_name}', not an image. Image analysis cannot be performed on non-image files."
            tags = ["error", "non-image", file_ext[1:], "unsupported"]
        
        return {
            "description": description,
            "tags": tags
        }
    
    def _generate_detection(self, file_name: str, file_ext: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate mock object detection results.
        
        Args:
            file_name: Name of the input file
            file_ext: File extension
            prompt: Optional prompt to guide generation
            
        Returns:
            Dictionary with detected objects and scene description
        """
        # Determine if this is an image file
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]
        is_image = file_ext in image_exts
        
        if is_image:
            # Generate realistic objects
            possible_objects = [
                {"name": "person", "location": "center", "confidence": 0.92},
                {"name": "chair", "location": "bottom right", "confidence": 0.83},
                {"name": "table", "location": "bottom center", "confidence": 0.76},
                {"name": "plant", "location": "top left", "confidence": 0.68},
                {"name": "window", "location": "background", "confidence": 0.88},
                {"name": "laptop", "location": "center", "confidence": 0.95},
                {"name": "book", "location": "bottom left", "confidence": 0.72},
                {"name": "cup", "location": "top right", "confidence": 0.84},
                {"name": "car", "location": "foreground", "confidence": 0.91},
                {"name": "tree", "location": "background", "confidence": 0.89}
            ]
            
            # Select random number of objects
            num_objects = random.randint(2, 6)
            objects = random.sample(possible_objects, num_objects)
            
            # Generate scene description based on detected objects
            object_names = [obj["name"] for obj in objects]
            description = f"The scene contains {', '.join(object_names[:-1])} and {object_names[-1]}."
            
        else:
            # Non-image file
            objects = []
            description = f"This appears to be a {file_ext[1:]} file named '{file_name}', not an image. Object detection cannot be performed on non-image files."
        
        return {
            "objects": objects,
            "description": description
        }
    
    def _generate_document(self, file_name: str, file_ext: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate mock document analysis results.
        
        Args:
            file_name: Name of the input file
            file_ext: File extension
            prompt: Optional prompt to guide generation
            
        Returns:
            Dictionary with extracted text and document type
        """
        # Determine if this is an image file
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]
        document_exts = [".pdf", ".doc", ".docx", ".txt"]
        is_image = file_ext in image_exts
        is_document = file_ext in document_exts
        
        if is_image or is_document:
            # Generate mock document content
            document_types = ["invoice", "report", "letter", "form", "article", "receipt", "memo"]
            document_type = random.choice(document_types)
            
            # Create text content based on document type
            if document_type == "invoice":
                text = f"""INVOICE #{random.randint(1000, 9999)}
Date: {datetime.now().strftime('%Y-%m-%d')}
Customer: Sample Company Inc.

Item 1: Product A  $29.99
Item 2: Service B  $50.00
Item 3: Maintenance  $75.50

Total: $155.49
"""
            elif document_type == "letter":
                text = f"""Dear Sir/Madam,

This is a sample letter generated for the file {file_name}.

Please consider this a demonstration of the mock model adapter's document analysis capabilities. This text is entirely generated and does not represent actual content from the file.

Sincerely,
Mock Model
"""
            else:
                # Generic content for other document types
                text = f"""DOCUMENT TYPE: {document_type.upper()}

This is a mock document analysis result for {file_name}.
The content is generated for testing purposes.

Section 1: Introduction
This document demonstrates the capabilities of the mock model adapter.

Section 2: Details
More details would normally be found here in a real document.

Section 3: Conclusion
This concludes the mock document analysis.
"""
        else:
            # Non-document file
            document_type = "unknown"
            text = f"This appears to be a {file_ext[1:]} file named '{file_name}'. Document analysis is best performed on document or image files."
        
        return {
            "text": text,
            "document_type": document_type
        }


def create_adapter(model_type: str = "mock", model_size: str = "small", **kwargs) -> MockModelAdapter:
    """
    Create a mock model adapter instance.
    
    Args:
        model_type: Type of model to simulate
        model_size: Size of model to simulate
        **kwargs: Additional parameters
        
    Returns:
        MockModelAdapter instance
    """
    return MockModelAdapter(model_type, model_size, **kwargs)


# Example usage when run directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mock Model Adapter")
    parser.add_argument("--file", required=True, help="Input file path")
    parser.add_argument("--mode", default="describe", choices=["describe", "detect", "document"], 
                       help="Analysis mode")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--size", default="small", choices=["small", "medium", "large"], 
                       help="Mock model size")
    
    args = parser.parse_args()
    
    # Create adapter and run prediction
    adapter = create_adapter(model_size=args.size)
    result = adapter.predict(args.file, mode=args.mode, output_path=args.output)
    
    # Print result
    print(json.dumps(result, indent=2))