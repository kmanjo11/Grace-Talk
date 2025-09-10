#!/bin/bash

# Run the OI Sandbox
echo "Starting OI Sandbox..."

# Check if Docker image exists
if ! docker images | grep -q oi-sandbox; then
    echo "OI Sandbox image not found. Building..."
    ./build.sh
fi

# Create workspace directory if it doesn't exist
mkdir -p workspace

# Run with docker-compose
docker-compose up -d

echo "OI Sandbox is running!"
echo "Access at: http://localhost:8501"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"
