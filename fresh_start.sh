#!/bin/bash

# =============================================================================
# Benten - Fresh Start / Reset Development Environment Script
# =============================================================================
# This script completely stops all running services, removes all containers,
# deletes database volumes, clears virtual environments, node modules, and caches,
# and then restarts the development environment completely fresh.
# =============================================================================

set -e

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================="
echo " 🧹 Benten Fresh Start / Reset Environment"
echo "====================================================="

# 1. Terminate any running host processes (uvicorn, celery, vite)
echo " 1. Stopping any running background servers and workers..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery -A app.workers.celery_app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# 2. Stop and remove Docker containers & volumes
echo " 2. Tearing down Docker containers, networks, and database volumes..."
if command -v docker &> /dev/null; then
    docker compose -f docker/docker-compose.yml down -v --remove-orphans 2>/dev/null || true
else
    echo "    (Docker not detected or not in PATH, skipping Docker teardown)"
fi

# 3. Clean Backend artifacts
echo " 3. Cleaning Python virtual environments and caches..."
rm -rf backend/venv
rm -rf backend/.env
rm -rf backend/test.db
rm -rf backend/.pytest_cache
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -type f -name "*.pyc" -delete 2>/dev/null || true

# 4. Clean Frontend artifacts
echo " 4. Cleaning Frontend dependencies and build caches..."
rm -rf frontend-benten/node_modules
rm -rf frontend-benten/dist
rm -rf frontend-benten/.vite

echo "====================================================="
echo " ✨ All services stopped, volumes wiped, and caches cleared!"
echo "====================================================="

# Check if --clean-only flag is passed
if [ "$1" = "--clean-only" ]; then
    echo " Clean-only mode specified. Exiting without starting servers."
    echo " Run './start_dev.sh' whenever you are ready to start afresh."
    exit 0
fi

echo " 🚀 Launching fresh development environment..."
echo "====================================================="
exec ./start_dev.sh
