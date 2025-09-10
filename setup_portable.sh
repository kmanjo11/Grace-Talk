#!/bin/bash

# OI Portable Setup Script
# Creates a portable Python environment for systems without Docker

echo "Setting up OI Portable Environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Create portable directory
PORTABLE_DIR="./oi-portable"
mkdir -p "$PORTABLE_DIR"

# Create virtual environment in user space (no admin rights needed)
echo "Creating virtual environment..."
python3 -m venv "$PORTABLE_DIR/venv"

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source "$PORTABLE_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Create run script
cat > "$PORTABLE_DIR/run.sh" << 'EOF'
#!/bin/bash
# OI Portable Run Script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Set environment variables from .env file if it exists
if [ -f "$SCRIPT_DIR/../.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/../.env" | xargs)
fi

# Create workspace directory
mkdir -p "$SCRIPT_DIR/../workspace"

# Run the app
cd "$SCRIPT_DIR/.."
streamlit run app.py --server.port 8501
EOF

chmod +x "$PORTABLE_DIR/run.sh"

# Copy necessary files
cp -r src "$PORTABLE_DIR/"
cp -r st_components "$PORTABLE_DIR/"
cp app.py requirements.txt models.json "$PORTABLE_DIR/"

echo "Portable setup complete!"
echo ""
echo "To run OI:"
echo "  cd oi-portable"
echo "  ./run.sh"
echo ""
echo "The entire oi-portable directory is self-contained and portable."
echo "Copy it to any system with Python 3.8+ and run it."
