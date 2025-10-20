#!/bin/bash

echo "🚀 Starting Core API Adapter Services"
echo "======================================"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use"
        return 1
    fi
    return 0
}

# Clean up any existing processes
echo "🧹 Cleaning up existing services..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "python.*server.py" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true
sleep 2

echo ""
echo "🔧 Starting Mock V1 API on port 8001..."
cd mock-v1-api
if check_port 8001; then
    python3 server.py &
    MOCK_PID=$!
    echo "✓ Mock V1 API started (PID: $MOCK_PID)"
else
    echo "✗ Failed to start Mock V1 API - port 8001 in use"
    exit 1
fi

echo ""
echo "🔧 Starting V2 Backend on port 8000..."
cd ../backend
if check_port 8000; then
    ./start.sh &
    BACKEND_PID=$!
    echo "✓ V2 Backend started (PID: $BACKEND_PID)"
else
    echo "✗ Failed to start V2 Backend - port 8000 in use"
    exit 1
fi

echo ""
echo "🔧 Starting Frontend on port 3000..."
cd ../frontend
if check_port 3000; then
    npm run dev &
    FRONTEND_PID=$!
    echo "✓ Frontend started (PID: $FRONTEND_PID)"
else
    echo "✗ Failed to start Frontend - port 3000 in use"
    exit 1
fi

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📍 Service URLs:"
echo "   Frontend:     http://localhost:3000"
echo "   V2 Backend:   http://localhost:8000"
echo "   V1 Mock API:  http://localhost:8001"
echo ""
echo "🛑 To stop all services: ./stop-all.sh"
echo ""
echo "Services are running in the background..."
echo "Press Ctrl+C to return to shell (services will continue running)"

# Wait for user interrupt
trap 'echo ""; echo "Services are still running in background. Use ./stop-all.sh to stop them."; exit 0' INT
read -p "Press Enter to return to shell (services will continue)..."