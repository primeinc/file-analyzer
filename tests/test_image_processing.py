#!/usr/bin/env python3
"""
Test the image processing to ensure it always processes
images regardless of current size.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from PIL import Image

# Add project root to system path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new module structure
from src.core.vision import VisionAnalyzer

def create_test_image(width, height, color=(255, 0, 0)):
    """Create a test image with specified dimensions and color."""
    # Create a temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
    os.close(temp_fd)
    
    # Create an image and save it
    img = Image.new('RGB', (width, height), color)
    img.save(temp_path)
    
    return temp_path

def test_image_processing():
    """Test that images are always processed regardless of size."""
    # Initialize the vision analyzer
    analyzer = VisionAnalyzer()
    
    # Test image sizes to try
    test_sizes = [
        # Same as target resolution
        (512, 512),
        # Different aspect ratios
        (800, 600),
        (600, 800),
        # Smaller than target resolution
        (256, 256),
        # Larger than target resolution
        (1024, 1024),
    ]
    
    # Process all the images and check the output
    for width, height in test_sizes:
        # Create a test image
        test_img = create_test_image(width, height)
        print(f"\nTesting image processing for {width}x{height} image")
        
        # Process the image
        processed_img = analyzer.preprocess_image(test_img)
        
        # Verify the processed image exists and is different from the original
        if processed_img and processed_img != test_img:
            # Check the dimensions of the processed image
            proc_img_obj = Image.open(processed_img)
            proc_width, proc_height = proc_img_obj.size
            
            # Check that it's at our target resolution
            target_width, target_height = map(int, analyzer.resolution.split('x'))
            
            print(f"Original: {width}x{height}")
            print(f"Processed: {proc_width}x{proc_height}")
            print(f"Target: {target_width}x{target_height}")
            
            # Check that the dimensions match the target (with some tolerance for aspect ratio preservation)
            assert proc_width <= target_width and proc_height <= target_height, \
                f"Processed image dimensions {proc_width}x{proc_height} exceed target {target_width}x{target_height}"
            
            # Clean up the temporary files
            os.remove(test_img)
            print(f"✅ Image {width}x{height} correctly processed")
        else:
            os.remove(test_img)
            print(f"❌ Failed to process {width}x{height} image")
            return False
    
    return True

if __name__ == "__main__":
    if test_image_processing():
        print("\n✅ All image processing tests passed")
        sys.exit(0)
    else:
        print("\n❌ Image processing tests failed")
        sys.exit(1)