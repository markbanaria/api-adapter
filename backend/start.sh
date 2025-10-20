#!/bin/bash

# Insurance API V2 Adapter Backend Startup Script

set -e  # Exit on any error

echo "🚀 Starting Insurance API V2 Adapter Backend..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -e \".[dev]\""
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python3 -c "import adapter" 2>/dev/null || {
    echo "❌ Backend dependencies not installed. Installing now..."
    pip install -e ".[dev]"
}

# Set environment variables
export V1_BASE_URL="http://localhost:8001"
export CONFIG_DIR="$SCRIPT_DIR/configs"
export LOG_LEVEL="INFO"

# Check if configs directory exists
if [ ! -d "configs" ]; then
    echo "📁 Creating configs directory..."
    mkdir -p configs
fi

# Count existing configurations
CONFIG_COUNT=$(ls -1 configs/*.yaml 2>/dev/null | wc -l | tr -d ' ')
echo "📋 Found $CONFIG_COUNT configuration files"

# Start the backend server
echo "🎯 Starting V2 Adapter API on http://localhost:8000"
echo "📚 API Documentation will be available at http://localhost:8000/docs"
echo "❤️  Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

cd src
exec python3 -m uvicorn adapter.main:app --reload --port 8000 --host 0.0.0.0