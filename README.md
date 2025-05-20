# File Analysis System

Unified tool for comprehensive file analysis combining:

- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract OCR: Text from images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis

## Usage

```bash
./analyze.sh [options] path_to_analyze
```

### Options

- `-a, --all`: Run all analyses
- `-m, --metadata`: Extract metadata
- `-d, --duplicates`: Find duplicates
- `-o, --ocr`: Perform OCR on images
- `-v, --virus`: Scan for malware
- `-s, --search TEXT`: Search content
- `-b, --binary`: Analyze binary files
- `-r, --results DIR`: Output directory

### Examples

```bash
# Run all analyses on a directory
./analyze.sh -a ~/Documents

# Extract metadata and scan for duplicates
./analyze.sh -m -d ~/Pictures

# Search for specific content
./analyze.sh -s "password" ~/Downloads

# OCR images in a directory
./analyze.sh -o ~/Screenshots
```

## Output

Results are saved to the current directory (or specified output directory):

- `analysis_summary_[timestamp].json`: Overall summary
- `metadata_[timestamp].json`: File metadata
- `duplicates_[timestamp].txt`: Duplicate files
- `ocr_results_[timestamp].json`: Text from images
- `malware_scan_[timestamp].txt`: Malware scan results
- `search_[text]_[timestamp].txt`: Content search results
- `binary_analysis_[timestamp].txt`: Binary analysis

## Using the Python Script Directly

```bash
./file_analyzer.py [options] path_to_analyze
```

Options are the same as the shell wrapper but use full format (e.g., `--metadata` instead of `-m`).