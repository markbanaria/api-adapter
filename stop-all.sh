#!/bin/bash

# Insurance API V1→V2 Adapter - Stop All Services Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping Insurance API V1→V2 Adapter Services${NC}"
echo "=================================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to kill processes on specific ports
kill_port() {
    local port=$1
    local service_name=$2

    if lsof -ti:$port >/dev/null 2>&1; then
        echo -e "${YELLOW}🔄 Stopping $service_name on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1

        if ! lsof -ti:$port >/dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo -e "${RED}❌ Failed to stop $service_name${NC}"
        fi
    else
        echo -e "${GREEN}✓ $service_name was not running${NC}"
    fi
}

# Stop services using PID files if they exist
if [ -d "logs" ]; then
    for service in qwen-model mock-v1-api v2-backend frontend; do
        if [ -f "logs/${service}.pid" ]; then
            pid=$(cat "logs/${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}🔄 Stopping $service (PID: $pid)...${NC}"
                kill "$pid" 2>/dev/null || true
                sleep 1
            fi
            rm -f "logs/${service}.pid"
        fi
    done
fi

# Kill by ports as backup
kill_port 3000 "Frontend"
kill_port 8000 "V2 Backend"
kill_port 8001 "Mock V1 API"

# Clean up any remaining processes
echo -e "${YELLOW}🧹 Cleaning up any remaining processes...${NC}"
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "uvicorn.*adapter" 2>/dev/null || true
pkill -f "uvicorn.*mock_v1_server" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All services have been stopped${NC}"
echo ""
echo -e "${YELLOW}💡 To start all services again: ./start-all.sh${NC}"