# Config Generator

AI-powered configuration generator for insurance API mappings using Qwen 7B.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run generator
generate-config --help
```

## Testing

```bash
pytest
```