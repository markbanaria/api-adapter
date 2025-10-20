#!/bin/bash

# Mock V1 Insurance API Startup Script

set -e  # Exit on any error

echo "🏭 Starting Mock V1 Insurance API..."

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
python3 -c "import uvicorn, fastapi" 2>/dev/null || {
    echo "❌ Dependencies not installed. Installing now..."
    pip install -e ".[dev]"
}

# Display available endpoints
echo "📋 Available Mock V1 Endpoints:"
echo "   GET /api/v1/customer/{customerId}"
echo "   GET /api/v1/policy/{id}"
echo "   GET /api/v1/coverage?policy_id={id}"
echo "   GET /api/v1/beneficiaries?policy_id={id}"
echo "   GET /health"

# Start the mock V1 server
echo ""
echo "🎯 Starting Mock V1 API on http://localhost:8001"
echo "❤️  Health check: http://localhost:8001/health"
echo "📚 Endpoint list: http://localhost:8001/"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

exec python3 -m uvicorn tests.mock_v1_server:mock_v1_app --port 8001 --host 0.0.0.0