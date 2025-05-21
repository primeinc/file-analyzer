# External Libraries

This directory contains external dependencies used by the File Analyzer system.

## FastVLM

The `ml-fastvlm/` directory contains Apple's FastVLM vision-language model integration.

### Installation

The model files are not stored in Git due to their size. Instead, they are downloaded 
automatically during first use or can be installed manually:

```bash
# Option 1: Install via pip (recommended)
pip install mlx mlx-fastvlm

# Option 2: Manual installation
git clone https://github.com/apple/ml-fastvlm.git libs/ml-fastvlm
cd libs/ml-fastvlm
git checkout v1.0.2  # Pin to specific version
pip install -e .
```

### Model Checkpoints

Model checkpoints are downloaded automatically on first use, or can be downloaded manually:

```bash
cd libs/ml-fastvlm
chmod +x get_models.sh
./get_models.sh
```

The checkpoints are stored in `libs/ml-fastvlm/checkpoints/` and are excluded from Git tracking.