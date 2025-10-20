# Insurance API Adapter - Backend

FastAPI-based adapter service for translating between V1 and V2 insurance APIs.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run development server
uvicorn adapter.main:app --reload --port 8000
```

## Testing

```bash
pytest
```