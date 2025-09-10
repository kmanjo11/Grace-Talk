#!/bin/bash

# Build the OI Sandbox Docker image
echo "Building OI Sandbox Docker image..."

# Build the Docker image
docker build -t oi-sandbox:latest .

# Optional: Tag for registry
# docker tag oi-sandbox:latest your-registry/oi-sandbox:latest

echo "Build complete!"
echo ""
echo "To run locally:"
echo "  docker-compose up"
echo ""
echo "To save for USB deployment:"
echo "  docker save oi-sandbox:latest > oi-sandbox.tar"
echo "  Copy oi-sandbox.tar to USB drive"
echo ""
echo "To deploy to cloud registry:"
echo "  docker login"
echo "  docker tag oi-sandbox:latest your-registry/oi-sandbox:latest"
echo "  docker push your-registry/oi-sandbox:latest"
