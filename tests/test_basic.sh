#!/bin/bash
# Basic test script for file_analyzer.py

# Create test directory
mkdir -p test_files
cd test_files

# Create sample text file
echo "This is a sample text file with some searchable content." > sample.txt
echo "It contains a sample password: P@ssw0rd123" >> sample.txt

# Create sample image file (1x1 pixel black PNG)
echo -e "\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c```\x00\x00\x00\x04\x00\x01\xa3\x17\x96Q\x00\x00\x00\x00IEND\xaeB\`" > sample.png

# Create duplicate file
cp sample.txt duplicate.txt

cd ..

echo "Running basic tests..."

# Test 1: Check if all tools are installed
echo "Test 1: Dependency check..."
python3 file_analyzer.py --skip-dependency-check -a test_files

# Test 2: Test metadata extraction
echo "Test 2: Metadata extraction..."
python3 file_analyzer.py --metadata test_files

# Test 3: Test duplicate detection
echo "Test 3: Duplicate detection..."
python3 file_analyzer.py --duplicates test_files

# Test 4: Test content search
echo "Test 4: Content search..."
python3 file_analyzer.py --search "password" test_files

# Test 5: Test with file filtering
echo "Test 5: File filtering..."
python3 file_analyzer.py --metadata --include "*.txt" test_files

# Clean up
echo "Cleaning up..."
rm -rf test_files

echo "All tests completed."