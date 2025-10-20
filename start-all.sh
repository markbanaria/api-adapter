#!/bin/bash

# Insurance API V1→V2 Adapter - Master Startup Script
# Starts all services: Mock V1 API, V2 Backend, Frontend, and Qwen Model

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🚀 Insurance API V1→V2 Adapter - Starting All Services${NC}"
echo "=================================================================="

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill processes on specific ports
kill_port() {
    local port=$1
    if check_port $port; then
        echo -e "${YELLOW}⚠️  Port $port is in use. Killing existing processes...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Kill any existing services
echo -e "${YELLOW}🧹 Cleaning up existing services...${NC}"
kill_port 3000  # Frontend
kill_port 8000  # Backend
kill_port 8001  # Mock V1 API

# Verify services are stopped
sleep 3

# Check if required directories exist
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Backend directory not found${NC}"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Frontend directory not found${NC}"
    exit 1
fi

if [ ! -d "config-generator" ]; then
    echo -e "${RED}❌ Config-generator directory not found${NC}"
    exit 1
fi

# Function to start a service in background with logging
start_service() {
    local name=$1
    local dir=$2
    local script=$3
    local port=$4
    local color=$5

    echo -e "${color}📡 Starting $name...${NC}"

    cd "$SCRIPT_DIR/$dir"
    if [ ! -f "$script" ]; then
        echo -e "${RED}❌ Script $script not found in $dir${NC}"
        exit 1
    fi

    # Make script executable
    chmod +x "$script"

    # Convert name to lowercase for file names
    local log_name=$(echo "$name" | tr '[:upper:]' '[:lower:]')

    # Start service in background
    ./"$script" > "../logs/${log_name}.log" 2>&1 &
    local pid=$!

    echo "$pid" > "../logs/${log_name}.pid"
    echo -e "${GREEN}✓ $name started (PID: $pid)${NC}"

    # Wait a moment for service to start
    sleep 3

    # Check if service is running on expected port
    if check_port $port; then
        echo -e "${GREEN}✓ $name is responding on port $port${NC}"
    else
        echo -e "${YELLOW}⚠️  $name may still be starting up on port $port${NC}"
    fi

    cd "$SCRIPT_DIR"
}

# Create logs directory
mkdir -p logs

# Start Qwen Model Service (if requested)
read -p "🤖 Start Qwen Model Service for AI config generation? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    start_service "Qwen-Model" "config-generator" "start-qwen.sh" "11434" "$PURPLE"
else
    echo -e "${YELLOW}⏭️  Skipping Qwen Model Service${NC}"
fi

# Start Mock V1 API
start_service "Mock-V1-API" "backend" "start-mock-v1.sh" "8001" "$CYAN"

# Start V2 Backend
start_service "V2-Backend" "backend" "start.sh" "8000" "$BLUE"

# Start Frontend
start_service "Frontend" "frontend" "start.sh" "3000" "$GREEN"

# Final status check
echo ""
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo "=================================================================="
echo -e "${CYAN}📱 Frontend UI:        ${NC}http://localhost:3000"
echo -e "${BLUE}🔧 V2 API & Docs:      ${NC}http://localhost:8000/docs"
echo -e "${CYAN}🏭 Mock V1 API:        ${NC}http://localhost:8001"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${PURPLE}🤖 Qwen Model:         ${NC}Available via CLI (generate-config)"
fi
echo ""
echo -e "${YELLOW}📋 Useful Commands:${NC}"
echo "  curl http://localhost:8000/health     # Check V2 backend"
echo "  curl http://localhost:8001/health     # Check V1 mock API"
echo "  curl http://localhost:8000/configs    # List configurations"
echo ""
echo -e "${YELLOW}📁 Log Files:${NC}"
echo "  tail -f logs/mock-v1-api.log         # Mock V1 API logs"
echo "  tail -f logs/v2-backend.log          # V2 Backend logs"
echo "  tail -f logs/frontend.log            # Frontend logs"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  tail -f logs/qwen-model.log          # Qwen Model logs"
fi
echo ""
echo -e "${RED}🛑 To stop all services: ./stop-all.sh${NC}"
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping all services...${NC}"

    # Kill services using PID files
    for service in qwen-model mock-v1-api v2-backend frontend; do
        if [ -f "logs/${service}.pid" ]; then
            pid=$(cat "logs/${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}Stopping $service (PID: $pid)...${NC}"
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "logs/${service}.pid"
        fi
    done

    # Also kill by port as backup
    kill_port 3000
    kill_port 8000
    kill_port 8001

    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

# Wait for user input to stop
echo -e "${GREEN}✨ All services are running! Press Ctrl+C to stop all services${NC}"
while true; do
    sleep 1
done