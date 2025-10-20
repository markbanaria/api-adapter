#!/usr/bin/env python3
"""
Demo script to run the FastAPI Insurance API Adapter
"""
import uvicorn
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "adapter.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )