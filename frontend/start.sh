#!/bin/bash

# Insurance API Mapping Viewer Frontend Startup Script

set -e  # Exit on any error

echo "🎨 Starting Insurance API Mapping Viewer Frontend..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ Dependencies not found. Installing now..."
    npm install
fi

# Check if Next.js is available
echo "🔍 Checking Next.js installation..."
npx next --version >/dev/null 2>&1 || {
    echo "❌ Next.js not found. Installing dependencies..."
    npm install
}

# Check for environment file
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local with default settings..."
    cat > .env.local << EOF
# Backend API URL
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Development settings
NODE_ENV=development
EOF
fi

# Display environment info
echo "🌍 Environment Configuration:"
if [ -f ".env.local" ]; then
    grep "NEXT_PUBLIC_API_BASE" .env.local || echo "   NEXT_PUBLIC_API_BASE=http://localhost:8000 (default)"
else
    echo "   NEXT_PUBLIC_API_BASE=http://localhost:8000 (default)"
fi

# Check if backend is running
echo "🔗 Checking backend connection..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Backend API is running on http://localhost:8000"
else
    echo "⚠️  Backend API not detected on http://localhost:8000"
    echo "   Make sure to start the backend first: cd ../backend && ./start.sh"
fi

# Start the frontend server
echo ""
echo "🚀 Starting Next.js Frontend with Turbopack..."
echo "🎯 Frontend will be available at http://localhost:3000"
echo "📱 Network access at http://$(hostname):3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

exec npm run dev -- --turbo