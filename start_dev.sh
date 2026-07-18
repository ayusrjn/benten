#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "============================================="
# Start Docker compose dependencies in the background
echo "🚀 1. Starting database, message broker, and cache containers..."
docker compose -f docker/docker-compose.yml up -d

# Check for backend/app/config environment setup
if [ ! -f backend/.env ]; then
    echo "📄 2. Creating backend/.env from .env.example..."
    cp backend/.env.example backend/.env
    # Adjust hostnames to localhost for running backend natively on host machine
    if [ "$(uname)" = "Darwin" ] || [ "$(expr substr $(uname -s) 1 5)" = "Linux" ]; then
        sed -i 's/POSTGRES_HOST=postgres/POSTGRES_HOST=localhost/g' backend/.env
        sed -i 's/RABBITMQ_HOST=rabbitmq/RABBITMQ_HOST=localhost/g' backend/.env
        sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/g' backend/.env
    fi
fi

# Set up Python virtual environment for backend
echo "🐍 3. Verifying Python virtual environment..."
cd backend
if [ ! -d venv ]; then
    echo "Creating virtual environment in backend/venv..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing/updating Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Set up Frontend packages
echo "📦 4. Verifying frontend dependencies..."
cd frontend
if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
cd ..

echo "============================================="
echo "🎉 Setup complete! Starting development servers..."
echo "Press Ctrl+C to stop all services simultaneously."
echo "============================================="

# Ensure all background jobs are stopped when script is killed or exits
trap 'echo -e "\nStopping all background tasks..."; kill $(jobs -p) 2>/dev/null; exit 0' INT TERM EXIT

# Start FastAPI backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start Celery worker
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info &
CELERY_PID=$!
cd ..

# Start Frontend
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Keep script running and wait on all background processes
wait
