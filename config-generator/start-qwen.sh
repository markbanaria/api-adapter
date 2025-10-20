#!/bin/bash

# Qwen Model Startup Script for Config Generation

set -e  # Exit on any error

echo "🤖 Starting Qwen Model Service..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first:"
    echo "   Visit: https://ollama.ai/"
    echo "   Or run: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

# Check if Ollama service is running
echo "🔍 Checking Ollama service..."
if ! ollama list >/dev/null 2>&1; then
    echo "🔄 Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    echo "⏳ Waiting for Ollama to start..."
    sleep 5

    # Verify Ollama is running
    if ! ollama list >/dev/null 2>&1; then
        echo "❌ Failed to start Ollama service"
        exit 1
    fi
fi

# Check if Qwen model is available
echo "🔍 Checking Qwen model availability..."
if ! ollama list | grep -q "qwen:7b"; then
    echo "📥 Qwen 7B model not found. Downloading now (this may take a while)..."
    echo "⏳ This is a ~4GB download, please be patient..."
    ollama pull qwen:7b
fi

# Verify model is working
echo "🧪 Testing Qwen model..."
if ! ollama run qwen:7b "Hello" --verbose=false >/dev/null 2>&1; then
    echo "❌ Qwen model test failed"
    exit 1
fi

# Check if config-generator dependencies are installed
if [ ! -d "venv" ]; then
    echo "📦 Setting up config-generator virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"
else
    source venv/bin/activate
    python3 -c "import generator" 2>/dev/null || {
        echo "📦 Installing config-generator dependencies..."
        pip install -e ".[dev]"
    }
fi

echo ""
echo "✅ Qwen Model Service Ready!"
echo "🎯 Model: qwen:7b"
echo "🔧 Config Generator CLI available: generate-config"
echo ""
echo "Example usage:"
echo "  generate-config \\"
echo "    --v2-spec specs/v2/policies-endpoint.json \\"
echo "    --v1-spec specs/v1/complete-v1-api.json \\"
echo "    --endpoint \"/api/v2/policies/{policyId}\" \\"
echo "    --output ../backend/configs/policies.yaml"
echo ""
echo "📋 Available commands:"
echo "  ollama list                    # List installed models"
echo "  ollama run qwen:7b \"prompt\"   # Test model directly"
echo "  generate-config --help         # Show config generator help"
echo ""
echo "Press Ctrl+C to stop (Ollama service will continue running)"
echo "=============================================================="

# Keep the script running to show it's active
trap 'echo "🛑 Qwen service monitoring stopped"' INT
while true; do
    sleep 30
    if ! ollama list >/dev/null 2>&1; then
        echo "⚠️  Ollama service appears to be down"
        break
    fi
done