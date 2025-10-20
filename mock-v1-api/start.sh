#!/bin/bash

echo "🚀 Starting Mock V1 Insurance API..."
echo "📍 This will run on http://localhost:8001"
echo "📚 API Documentation: http://localhost:8001/docs"
echo ""

cd "$(dirname "$0")"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Install required packages if needed
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "📦 Installing required packages..."
    pip3 install fastapi uvicorn[standard]
}

echo "🎯 Starting server..."
python3 server.py