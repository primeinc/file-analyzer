# FastVLM Integration

This directory contains Apple's FastVLM vision-language model integration.

## Version Information

We use FastVLM v1.0.2 for consistent results. The CI workflow and installation scripts
are configured to use this specific version.

## Setup

The model code and weights are not stored in Git. They are automatically installed during
the CI workflow process or on first use.

To install manually:

```bash
# Clone the repository
git clone https://github.com/apple/ml-fastvlm.git .
git checkout v1.0.2  # Pin to specific version
pip install -e .

# Download model weights
chmod +x get_models.sh
./get_models.sh
```

## Model Variants

FastVLM is available in multiple sizes:
- 0.5B parameters (fastest)
- 1.5B parameters (default)
- 7B parameters (highest quality)

The installation script downloads all variants.