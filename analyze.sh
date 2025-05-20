#!/bin/bash
# Wrapper for file_analyzer.py

# Determine script directory even if run through a symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

ANALYZER="${SCRIPT_DIR}/file_analyzer.py"

if [ $# -eq 0 ]; then
    echo "Usage: $0 [options] path_to_analyze"
    echo "Options:"
    echo "  -a, --all             Run all analyses"
    echo "  -m, --metadata        Extract metadata"
    echo "  -d, --duplicates      Find duplicates"
    echo "  -o, --ocr             Perform OCR on images"
    echo "  -v, --virus           Scan for malware"
    echo "  -s, --search TEXT     Search content for TEXT"
    echo "  -b, --binary          Analyze binary files"
    echo "  -r, --results DIR     Output directory"
    echo "  --skip-checks         Skip dependency checks"
    echo "  -q, --quiet           Quiet mode with minimal output"
    echo "  -i, --include PATTERN Include only files matching pattern (can be used multiple times)"
    echo "  -x, --exclude PATTERN Exclude files matching pattern (can be used multiple times)"
    echo "  -c, --config FILE     Path to custom configuration file"
    exit 1
fi

OPTIONS=""
SEARCH_TEXT=""
OUTPUT_DIR=""
TARGET_PATH=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            $ANALYZER -h
            exit 0
            ;;
        -a|--all)
            OPTIONS="$OPTIONS --all"
            shift
            ;;
        -m|--metadata)
            OPTIONS="$OPTIONS --metadata"
            shift
            ;;
        -d|--duplicates)
            OPTIONS="$OPTIONS --duplicates"
            shift
            ;;
        -o|--ocr)
            OPTIONS="$OPTIONS --ocr"
            shift
            ;;
        -v|--virus)
            OPTIONS="$OPTIONS --malware"
            shift
            ;;
        -s|--search)
            SEARCH_TEXT="$2"
            OPTIONS="$OPTIONS --search \"$SEARCH_TEXT\""
            shift 2
            ;;
        -b|--binary)
            OPTIONS="$OPTIONS --binary"
            shift
            ;;
        -r|--results)
            OUTPUT_DIR="$2"
            OPTIONS="$OPTIONS --output \"$OUTPUT_DIR\""
            shift 2
            ;;
        --skip-checks)
            OPTIONS="$OPTIONS --skip-dependency-check"
            shift
            ;;
        -q|--quiet)
            OPTIONS="$OPTIONS --quiet"
            shift
            ;;
        -i|--include)
            OPTIONS="$OPTIONS --include \"$2\""
            shift 2
            ;;
        -x|--exclude)
            OPTIONS="$OPTIONS --exclude \"$2\""
            shift 2
            ;;
        -c|--config)
            OPTIONS="$OPTIONS --config \"$2\""
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            TARGET_PATH="$1"
            shift
            ;;
    esac
done

# Ensure target path is provided
if [ -z "$TARGET_PATH" ]; then
    echo "Error: No target path specified"
    exit 1
fi

# Run the analyzer
echo "Running analysis on $TARGET_PATH"
eval "${ANALYZER} ${OPTIONS} \"${TARGET_PATH}\""